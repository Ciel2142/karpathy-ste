# explain-onboard-events: execution brief (one wave, high risk)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this brief task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/superpowers/specs/2026-10-16-explain-onboard-design.md`, section 16 (16.1 to 16.8, with the five calls after the builder check). The spec is authoritative; this brief carries contracts only.

**Risk:** high. The map format is a compatibility contract: a map written before this change fails the check (`section: missing Events`), and the inventory output gains a kind and a new summary line that `course/map-task.md` and the rung file quote.

**Coverage:** not opted in. One wave, nothing deferred, so no wave map.

## 1. Goal and observable done-when

Goal: the onboarding map names each event of an event-based service in an `Events` section (type, optional payload, stream, emitters, consumers, each cited), `onboard.py check` enforces it, `onboard.py inventory` finds event declarations that the map must name or dismiss, and the onboarding page shows an events × components matrix whose marks link to the flows.

Done when:

- `cd skills/explain && python3 -B -m unittest discover -s tests` passes in full.
- `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/onboard.md` prints `0 errors, 0 warnings`.
- The diadoc output `~/karpathy/out/2026-10-17-210343-onboard-diadoc/`, extended by hand (Task 6), prints `onboard: ok` from `onboard.py check map.md --root /Users/valukin/work/diadoc --inventory inventory.txt` after a fresh `onboard.py inventory`, and `verify.sh` on its `index.html` prints every line `ok` and `bpmn: none`.

## 2. Current-code facts that constrain the change

- `scripts/onboard.py` (722 lines). `TITLES` holds twelve titles; `parse_map` opens a `### ` scope only when the current section is `Flows` (`Flow(ident, heading, question, line, diagrams, facts)`); every other `### ` line is dropped, and a `- ` line under `Events` would become a section fact. `Section` is a `NamedTuple(title, line, diagrams, facts, flows, none_found)`.
- `_fact` splits on ` | ` into fact and cite; `keyed(fact)` returns `(key, rest)` when the head before `:` is one `TOKEN`; `none_found(fact)` is `<key>: none found`; `HANDLE` is the backticked-text pattern; `ID` is `[a-z][a-z0-9_-]*`.
- `check_map` order: sections, places, `_entry_lines`, `_handle_lines`, `_shape_lines`, `_convention_lines`, `_where_lines`, `_cite_lines`, `_unlisted_lines`. `_cite_scopes` walks `TITLES` and adds `Flows/<id>` scopes; `_may_lack_cite` exempts `none found` in `Shape` commands and `Conventions`.
- `PATTERNS` is a dict of kind → rules, tried in order, one kind per line (`_kind_of`). `ENTRY_KINDS = tuple(PATTERNS)` feeds `_entry_lines` and the drift test. `_declares_type(lines, index)` is a look-ahead past `@` lines to a `TYPE_DECL` line. `scan_file` emits `Hit(path, line, kind, text)` at the matched line. `cmd_inventory` prints `inventory: %d entry points`.
- `_unlisted_lines` requires every tabbed inventory line to be cited by an `Entry points` fact; it does not look at the kind column.
- `_where_required` derives the required `Where to look` keys; `WHERE_KEYS` is a tuple that `test_rung_drift.py` reads as bullet heads.
- Tests: `tests/test_onboard.py` (`GOOD` parse-only map, `PLANTED` list of 18 inventory hits asserted exactly against `tests/fixtures/onboard/tree`, `CheckCase` over `tests/fixtures/onboard/map.md`); course fixture maps `tests/fixtures/course/map/svc-a.md` and `docs-b.md` go through `onboard.py check` and need the new section; `tests/test_rung_drift.py` `OnboardRungCase` locks the eight rules, the kinds table (== `onboard.PATTERNS` order), twelve titles, ten prefixes and the plan bullets of `rungs/onboard.md`.
- Page: `templates/page.html` has `.table-wrap { overflow-x: auto; }` and a `table.status` example; no `table.matrix`. The onboard fixture page is `tests/onboard_page.py` + `tests/fixtures/onboard-page/section.html`, exercised by `test_verify.py` (`verify.sh` six lines) and `test_bpmn_check.py`.
- Leftover issue kp-xc77 (open, P3) touches the inventory pattern table (Go `NewReader(` anchoring, Camel `- route:`). Out of scope here; do not fix it in passing.

## 3. Consumed and produced interfaces

Consumed: `Fact`, `Flow`, `Section`, `MapDoc`, `keyed`, `none_found`, `HANDLE`, `ID`, `TOKEN`, `NONE_FOUND`, `cite_check.fact_problems`, `_declares_type`, `TYPE_DECL`, `Hit`.

Produced (declarations only):

```python
TITLES  # thirteen: "Events" inserted after "State"
EVENT_KEYS = ("type", "payload", "stream", "emits", "consumes")
EVENT_REQUIRED = ("type", "stream", "emits", "consumes")
EVENT_ONCE = ("type", "payload", "stream")
ENTRY_KINDS  # ("http", "listener", "route", "schedule", "main"): PATTERNS keys without "event"
WHERE_KEYS   # gains "add-event" after "add-transform"

class Event(NamedTuple):
    name: str
    line: int
    facts: list[Fact]

# Section gains a field `events: list[Event]`, empty for every section other than Events.
def _event_lines(doc: MapDoc) -> list[str]: ...      # the `event` and `events` prefixes of spec 16.3
def event_slug(name: str) -> str: ...                # lowercase, runs outside [a-z0-9] -> "-", stripped
```

`onboard.py inventory` output: one tabbed line per hit as today, kind column `event` for the new hits; last line `inventory: <n> entry points, <m> event types`.

## 4. Invariants and named failure behavior

- A map with no `Events` section reports `section: missing Events` and nothing else new (no crash in `_event_lines`, `_where_required` or `_cite_scopes`).
- `Events` with `none found` and no dismissals: no `event` lines; any inventory `event` hit is still reported (`inventory <path>:<line>: not in Events`).
- `event` hits never appear in `inventory ... not in Entry points`, and entry hits never in `... not in Events`.
- `- emits: none found` / `- consumes: none found` carry no cite and give no `cite Events/<name>#<n>: no cite`; every other event line without a cite does.
- `outside:` lines need a backticked handle (`no component in backticks` otherwise). An `ignores:` consume is a component line and needs its backticked component.
- An `event <name> #<n>: unknown key` line for a keyless line reports its first word, or `none`, as `_shape_lines` does.
- Event names are compared verbatim (case and punctuation kept); `event <name>: twice` is printed once per repeated name.
- One declaration gives one `event` hit, at the declaration line, even when an annotation line above it and the name suffix both match.
- `@EventSourcingHandler` is never a hit of any kind; `@EventListener` stays `listener`; `@Event\b` does not match `@EventListener` or `@EventHandler`.
- Exit codes and the last line of `check` keep their meaning (0 ok, 1 failures, 2 unreadable).

## 5. Rollback

Code-local and reversible: revert the branch merge. Maps written under the new format would fail the old check on `section: Events` order/unknown only if the old check were restored; no data migrates.

## 6. Acceptance evidence and run commands

- Per task: `cd skills/explain && python3 -B -m unittest tests.test_onboard` (Tasks 1 to 3), `tests.test_rung_drift` (Task 4), `tests.test_verify tests.test_page_template tests.test_bpmn_check` (Task 5); decisive line `OK`.
- Rung lint: `python3 skills/ste/scripts/ste_lint.py skills/explain/rungs/onboard.md` → `0 errors, 0 warnings`.
- Branch end: `cd skills/explain && python3 -B -m unittest discover -s tests` → `OK`.
- Proof (Task 6): `onboard: ok`; `verify.sh` all `ok`, `bpmn: none`.

## 7. Ordered tasks and ownership

Branch `feat/explain-onboard-events`, worktree `/Users/valukin/karpathy-wt/explain-onboard-events`. Tasks run in order; Task 5 may run beside Tasks 2 to 4 (it owns only the template and the onboard page fixture).

### Task 1: Parse and check the `Events` section

Files: `scripts/onboard.py`; `tests/test_onboard.py`; `tests/fixtures/onboard/map.md` and new source files under `tests/fixtures/onboard/tree`; `tests/fixtures/course/map/svc-a.md`, `docs-b.md`.

Contract: `TITLES` gains `Events` after `State`. `parse_map` opens an `Event` scope on `### <name>` under `Events` (name = heading text, stripped), and `- ` lines before the first entry are section facts (the dismissals). `_event_lines` runs after `_entry_lines` and prints, per spec 16.3 and in this order: dismissal faults (`events #<n>: not a dismissal` for a section fact whose fact does not start with `not an event:` followed by a backticked name and a reason); then per entry in map order: `twice` (once per repeated name, at the second entry), `missing <key>` in `EVENT_REQUIRED` order, `<key> twice` for `EVENT_ONCE`, then per line `unknown key`, `no component in backticks`, `flow <id> not in Flows` (the ` -> <id>` tail, as `_entry_lines` reads it), and `none found beside a line` once per key. `_cite_scopes` adds `Events` (dismissals) and `Events/<name>` scopes; `_may_lack_cite` exempts `emits`/`consumes` `none found`. The fixture map gains `## Events` with two entries on two new tree files (`OrderPlacedEvent.java` record, an emitter and a consumer in existing or new tree classes; one entry with an `outside:` consumer and a `payload` line); the course fixture maps gain `## Events` + `none found`. Tests (one each): good fixture still `onboard: ok`; each line of the 16.3 table; `none found` without cite passes; `none found` beside a component line fails; `outside:` without a handle fails; missing section gives exactly `section: missing Events`; `parse_map` of an entry keeps its name verbatim (`event.document.signature`).

### Task 2: Inventory `event` hits and their coverage

Files: `scripts/onboard.py`; `tests/test_onboard.py`; tree fixtures.

Contract: `PATTERNS` gains `event` last (JVM: a `class|record|interface|object` declaration whose name ends in `Event`, `extends ApplicationEvent`, `@DomainEvent` and `@Event\b` on a type; Go: `type \w+Event struct`). `listener` gains `@EventHandler`, `@SagaEventHandler`, `@CommandHandler` (JVM) and `SubscribeTo\w*\(` (Go). `ENTRY_KINDS` excludes `event`. An annotation `event` hit moves to the declaration line found by the `_declares_type` look-ahead, takes that line's text, and merges with a suffix hit on the same line; an annotation with no declaration after it is no hit. `cmd_inventory` prints `inventory: <n> entry points, <m> event types`. `_unlisted_lines` checks entry hits against `Entry points` cites and `event` hits against `type`, `payload` and dismissal cites of `Events` (`inventory <path>:<line>: not in Events`). `PLANTED` grows by the new tree hits and its count assertion follows. Tests: each new pattern hits once with the right kind; `@EventSourcingHandler`, `class EventPoller`, `EventEnvelope` give no hit; annotation on its own line hits at the declaration; annotation + suffix on one declaration is one hit; CLI summary line; an unnamed event hit fails the check with the `not in Events` line and a dismissal clears it; an event hit is never reported as `not in Entry points`.

### Task 3: `add-event` in `Where to look`

Files: `scripts/onboard.py`; `tests/test_onboard.py`; fixture map.

Contract: `WHERE_KEYS` gains `add-event`; `_where_required` requires it when `Events` has at least one entry. Tests: fixture with entries and no `add-event` line → `where: missing add-event`; `Events` `none found` → not required.

### Task 4: Rung file, course override and drift tests

Files: `rungs/onboard.md`; `course/map-task.md`; `tests/test_rung_drift.py`.

Contract (spec 16.2 to 16.6): "Explore the service" gains rule 6 "Events" (nine rules; later ones renumbered), the inventory paragraph names the `event` kind and the new summary line, the kinds table gains the `event` row last and the new `listener` patterns, `add-event` is a bullet of rule 8. "The map": skeleton with `## Events` (dismissal line, `### <event-name>`, the five keyed lines), format rules of 16.3 including the slug, prefix table gains the `event` and `events` rows and the `not in Events` inventory form (twelve prefixes). "Plan the sections": a `#events` bullet after `#state` with the matrix (`.table-wrap > table.matrix`, `E`/`C`/`(C)`, links to `#flow-<flow-id>`, the gaps column, one `details.walk` per event with id `event-<slug>`, a `div.cites` after the table, omitted when `Events` has no entry); the nav and glossary sentences. `course/map-task.md`: the `none found` override adds `Events`. Drift tests: nine rule starts, the kinds table equals `onboard.PATTERNS` (six kinds), `ENTRY_KINDS` five, thirteen titles, the `### <event-name>` skeleton line, twelve prefixes, `EVENT_KEYS` and `add-event` as bullet heads, the `#events` bullet in order between `#state` and `#formats`. The STE lint of `rungs/onboard.md` is clean.

### Task 5: The matrix style and the onboard fixture page

Files: `templates/page.html`; `tests/fixtures/onboard-page/section.html`; `tests/onboard_page.py` (nav entry); `tests/test_page_template.py` if it locks the CSS block.

Contract: `table.matrix` style: mark cells centered, the first column sticky (`position: sticky; left: 0` with the page background), header cells may wrap; type sizes stay those of `th`/`td` so the font guard passes at 500 px. The fixture section gains an `#events` section with a three-event × three-component matrix, one link mark, one `(C)` mark, one `details.walk` with id `event-<slug>`, and a `div.cites` whose cite resolves against the fixture. Tests: `test_verify` onboard case still prints the six `ok` lines; the snapshot shows no horizontal page scroll at the narrow width.

### Task 6: Proof on the diadoc output (untracked)

Files: `~/karpathy/out/2026-10-17-210343-onboard-diadoc/` only. Never commit `out/`.

Contract: rerun `onboard.py inventory` over `/Users/valukin/work/diadoc` into `inventory.txt`; add `## Events` to `map.md` with every routing key of `EventClassifier` plus `event.unknown`, `DiadocAuthorizedEvent`, `DiadocDeauthorizedEvent`, `ApplicationReadyEvent`, `BoxEvent` as `payload`, `StaleEvent` named or dismissed by what the code does; `DocumentEventConsumer`'s default branch as `ignores:` consumes; `add-event` under `Where to look`; renumber nothing else. Then add the `#events` section and nav link to `index.html` per Task 4's plan bullet, and run `mermaid_svg.py inline`, `onboard.py check` and `verify.sh`. Evidence: the two decisive lines in the task close reason, and a look at `page.png` / `narrow.png` for the matrix.

## Review focus

1. `_unlisted_lines` must split hits by kind; a regression here makes every entry point a `not in Events` failure or hides event hits. Task 2.
2. The annotation look-ahead must not walk past a non-annotation line (`_declares_type` semantics) and must not double-count. Task 2.
3. `parse_map` must keep `### ` under any other section ignored, as today; only `Events` and `Flows` open scopes. Task 1.
4. The `## Events` position: `State` then `Events` then `Formats and transforms`; `section: Events out of order` when moved. Task 1.
5. The drift test must read kinds from `onboard.PATTERNS` and entry kinds from `onboard.ENTRY_KINDS`, not literals only. Task 4.
