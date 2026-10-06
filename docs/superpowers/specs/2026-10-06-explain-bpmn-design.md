# explain: BPMN subjects — the file's own diagram, readable cites, and sub-process coverage

Date: 2026-10-06. Status: draft for user review. Coverage: not opted in.

## 1. Problem

Two faults of the first lesson live run (`/explain /Users/valukin/work/aos --as lesson`,
output `out/2026-10-06-145908-lesson-aos`), both reported by the user on 2026-10-06.

The cites of a BPMN claim are unreadable. A claim about the process cites lines such as
`aos.bpmn:2300 sourceRef="Gateway_08et0jy" targetRef="Gateway_0y0fw3a"`. Element ids carry no
meaning for a reader; the user called them "random references to bpmn schema, which i just don't
understand" and asked for a visualisation of the process.

The page flattens the inside of a stage. The extended personal-data check got one section with
one sentence per sub-process; the inner parts — the sanction sub-process with its bypass flag,
the three SMEV sub-processes with their timeouts, the manual-check user tasks, the refusal
gateway — were compressed or dropped. The user: "you entirely skipped part of extended check, or
internal subprocesses". Nothing in the rung rules required their coverage, and nothing checked it.

Both faults belong to the skill, not to that lesson. That lesson is the test case for the fix.

### 1.1 What the subject file offers

`aos.bpmn` is a Camunda Modeler 5 file. It carries its own diagram: a `bpmndi:BPMNShape` with
`dc:Bounds` for each node, a `bpmndi:BPMNEdge` with waypoints for each flow, `bpmndi:BPMNLabel`
bounds for edge names. Collapsed sub-processes use the drilldown layout: each has its own
`bpmndi:BPMNPlane`. The file has 11 planes (the main collaboration and ten sub-processes) and 17
`subProcess` elements; expanded sub-processes (the SMEV checks, the event sub-processes) have
their shapes inside their parent's plane. The picture a reader needs is in the file; the skill
only has to draw it.

## 2. Design

A stdlib Python tool, `scripts/bpmn.py`, with four subcommands: `planes`, `svg`, `label`,
`check`. Rung rules in `page.md` (inherited by `lesson.md`) that require one diagram per plane
and a paragraph per inner part. One new line in `verify.sh`. Clips are unchanged.

### 2.1 The renderer: `bpmn.py svg`

Call:

```
bpmn.py planes <file.bpmn>
bpmn.py svg <file.bpmn> --plane <id> [--highlight id,id,…] [--prefix <p>]
```

`planes` prints one line per `bpmndi:BPMNPlane`: the `bpmnElement` id, the element's name, the
line of the element's opening tag. `svg` prints one SVG to stdout. `--plane` defaults to the
first plane of the file. An unknown plane id exits 2 and prints the plane list on stderr.

Parsing uses `xml.etree` only. Two indexes over the file: the model (id → kind, name, parent,
attributes) and the line map (id → line of the opening tag, from a scan of the text, because
etree drops line numbers). The DI of the chosen plane gives shapes (`BPMNShape`, `dc:Bounds`,
`isExpanded`), edges (`BPMNEdge`, `di:waypoint`) and `BPMNLabel` bounds.

The output is one inline SVG in the page palette: `class="bpmn"`, `role="img"`, a `<title>`
with the plane's name, `data-ste="skip"`, `data-plane="<id>"`. Coordinates are the DI units
unchanged. `viewBox` is the bounding box of the plane's shapes, edges and labels plus a margin
of 20 units. `width` and `height` are set in px at 1 unit = 1 px. Every drawn element carries
`data-id="<bpmn id>"`. Shapes by kind, in the notation Modeler draws:

| Kind | Shape |
|---|---|
| task (service, send, receive, user, business rule, script, plain) | rounded rect; a small kind tag in the top-left corner (`service`, `send`, `receive`, `user`, `rule`, `script`) in place of Modeler's icons |
| sub-process, expanded | rect, name along the top edge, children drawn inside |
| sub-process, collapsed | rect with the `+` marker at the bottom centre |
| event sub-process | as above, dotted border |
| exclusive / parallel / event-based gateway | diamond with `×` / `+` / the pentagon in a double circle |
| start / intermediate / end event | circle: thin / double / thick stroke; markers for timer (clock), message (envelope), error (lightning), link (arrow), `terminate` (filled disc) |
| boundary event | the event circle where the DI puts it; dashed for `cancelActivity="false"` |
| participant, lane | rect with the name rotated 90° along the left edge |
| text annotation | left bracket and text; its association as a dotted line |
| sequence flow | polyline through the waypoints, arrowhead at the end; the default flow of a node gets the slash near its source; the flow's name at its `BPMNLabel` bounds |
| message flow | dashed polyline, open arrowhead |

Text: names are copied verbatim from `name=`; Russian stays Russian, the prose carries the
English. Font size is 14 units — the page's floor — wrapped to the shape's width at an estimate
of 0.55 em per character, word by word. A name that does not fit the shape's height is cut at
the last line that fits and ends with `…`; the full name goes into the element's `<title>`. Text
never shrinks: a wide plane does not scale down, `figure.bpmn` scrolls horizontally (the aos main
plane is 948 × 1580 units: no scroll at 1440 px, a scroll on a phone). This keeps the SMALLTEXT
guard honest.

Highlights: each id in `--highlight` gets `class="hl"`, drawn with the terracotta accent as
stroke and a light terracotta fill. Marker ids (arrowheads) and `<title>` ids get `--prefix`, so
that one plane can render twice in one page (a steps player that highlights other elements per
step). Without `--prefix`, the plane id is the prefix.

Faults: a shape without bounds or an edge with fewer than two waypoints is skipped with a
warning on stderr; a model element without any DI shape is not drawn. Output is deterministic:
document order, no randomness, byte-equal on a second run.

### 2.2 Rung rules in `page.md`

Plan the sections, for a directory subject whose main flow is a BPMN file:

- The first section (the whole, start to end) carries the main plane, with the stages
  highlighted.
- Then one section per stage: each collapsed sub-process that the main plane reaches, in process
  order. The section opens with that stage's plane diagram and a lead paragraph. Then, one
  paragraph each, with cites: every sub-process inside the plane (expanded, or a nested collapsed
  one), every gateway with its branches named, every user task, every boundary timer or error
  that changes the path.
- A nested collapsed sub-process (its own plane inside a stage, like `AOS_BASIC_PD_CHECK` inside
  `QUESTIONNAIRE`) gets its own diagram too: a second `figure.bpmn` in the stage section when it
  is small, or its own section when it carries several decisions. Every plane renders somewhere.
- Siblings of the same shape (the three SMEV checks) get one paragraph for the pattern — send,
  wait, timeout, code — then one sentence per sibling with what differs: the service, the
  message, the code variable.
- The mechanics sections follow as today: handlers, delegates, decision tables, deployment.
- The section count follows the planes. The "about twelve" guidance bends for a BPMN subject;
  a merge may not drop a plane. `Not covered` lists any plane or sub-process that the page does
  not explain, by its name verbatim.

Diagram pattern "BPMN plane": a flow that lives in a `.bpmn` file is never drawn by hand with the
flow pattern. It renders with `bpmn.py svg` into:

```html
<figure class="bpmn">
  <!-- output of: bpmn.py svg <file> --plane <id> --highlight <ids the paragraphs cite> -->
  <svg class="bpmn" …>…</svg>
  <figcaption>One STE sentence: what this plane is.</figcaption>
</figure>
```

The flow, sequence and layers patterns stay for code paths. The page template gets the CSS for
`figure.bpmn` (horizontal scroll, the palette of the shapes, `.hl`) and for the cite label
(2.3).

Cites for BPMN: cite the opening-tag line of the element (its id line), its `name=` line, the
sequence flow or its condition line. The label tool makes any of these readable, so the author
cites the line that carries the fact, not the line that reads best.

The "Verify and fix" list of the page rung gains three commands, in this order: `bpmn.py svg`
per plane (while writing), `bpmn.py label index.html` after the cites are written, then
`verify.sh` (which runs `check`).

Lesson (`lesson.md`): `review/plan.md` is unchanged in form; plan step 2 reads the planes as the
section candidates. `lesson/review-page.md` gains one check: "for each sub-process, gateway and
user task in the section's diagram, a paragraph explains it; the names in the prose match the
diagram." Clips are unchanged: bespoke films, not DI renders; a clip's script cites the same
element lines as the section.

### 2.3 Cite labels: `bpmn.py label`

```
bpmn.py label <index.html>
```

Rewrites `index.html` in place. For every `<cite>` whose `data-path` ends in `.bpmn`, it reads
the file at `data-root/data-path` (root from `#provenance`), finds the element that owns line
`data-line`, and writes a label into the cite. Idempotent: an existing label is replaced.

The owner of a line is the innermost element whose opening tag starts at or before the line and
whose closing tag ends at or after it. The label:

| Owner | Label |
|---|---|
| flow node (task, gateway, event, sub-process) | its `name`; without a name: `<kind> <id>`, e.g. `exclusive gateway Gateway_08et0jy` |
| `sequenceFlow`, or a `conditionExpression` inside one | `<source name> → <target name>`; the flow's own name appended after a comma when it has one |
| `message`, `error`, `signal` | its `name`; for an error also its `errorCode` |
| a DI shape, edge or label | the label of its `bpmnElement` |
| `process`, `collaboration`, `participant`, `lane`, `definitions`, content of `extensionElements` | the owner's `name`, else `<kind> <id>` |

A node without a name inside a `→` label is written as `<kind> <id>` too. Names are copied
verbatim, like snippets; the credential rule of convention 2 applies to them unchanged.

A `data-line` that resolves to no element (a blank line, a comment, a line past the end) is a
fault: `label` exits 1 and lists those cites as `<section id> | <path>:<line> | no element`. The
author moves the cite to a line that carries a fact.

Markup, inside the cite after the `<code>`:

```html
<cite data-path="src/main/resources/aos.bpmn" data-line="2300" data-snippet="…">
  aos.bpmn:2300 <code>sourceRef="Gateway_08et0jy" targetRef="Gateway_0y0fw3a"</code>
  <span class="bpmn-label">Нет совпадений → Начало проверок перс данных в гос сервисах СМЭВ</span>
</cite>
```

The visible `basename:line` stays, so `cite_check.py` is unchanged. Two CSS rules in the page
template: `.bpmn-label` in ink, at the body size, on its own line; `cite:has(.bpmn-label) > code`
muted and smaller, never under 14 px. The label leads the eye; the raw line stays available.

### 2.4 Coverage check: `bpmn.py check`, and `verify.sh`

```
bpmn.py check <index.html>
```

Inputs: the page, its `data-root`, and every `.bpmn` file it cites. For each such file the check
collects the plane ids and all `subProcess` ids with their names. Four conditions:

1. Every plane is rendered: an `svg.bpmn[data-plane="<id>"]` exists in the page, or
   `p.not-covered` holds the plane's name verbatim (its id, for a plane whose element has no
   name, such as a collaboration).
2. Every sub-process is explained: at least one cite resolves (by the rule of 2.3) to that
   element itself — its own lines, not a descendant's — or `p.not-covered` holds its name
   verbatim. Appearing in a diagram is not explanation, so this counts cites, not `data-id`s.
3. Every BPMN cite carries a label, and the label equals what `label` would write now: no stale
   and no hand-typed label.
4. Every `svg.bpmn` matches the file: its `data-plane` is a plane of a cited file, and each
   `data-id` inside it is an element of that file. This catches a diagram pasted from another run.

Output follows `cite_check.py`: one line per failure, `<section id> | <condition> | <what>`; a
summary line; exit 0 (pass), 1 (failures), 2 (usage: no argument, unreadable page, no
`data-root`). A page that cites no `.bpmn` file passes with the summary `bpmn: none`.

`verify.sh` gains one line after `media`, for the sheet, page and lesson rungs:
`bpmn: ok | none | FAIL <n> failure(s)`, detail lines indented by two spaces as for citations.
The header comment's counts move up by one; `test_verify.py` adjusts.

## 3. Tests

System `python3`, stdlib only, as the other tests of `skills/explain/tests`.

Fixtures: `tests/fixtures/two_planes.bpmn`, hand-written, about 150 lines, Russian names. Main
plane: start event, a collapsed sub-process `STAGE_A`, an exclusive gateway with a default flow
and two named flows, an expanded event sub-process with a timer start, an end event. Second
plane, for `STAGE_A`: a service task with a timer boundary, a send task, a receive task, a
`terminate` end, one text annotation. `tests/fixtures/bpmn_page.html`: a page on the template
with both planes rendered, labelled cites, and a `#provenance` whose `data-root` is the fixtures
directory.

- `test_bpmn_svg.py`: `planes` lists both planes with names and lines; `svg` of each plane has
  `viewBox`, `<title>`, `data-plane`, one `data-id` per DI shape and edge, the kind tags, the `×`
  and `+` markers, a dotted event sub-process, the default-flow slash; `--highlight` adds
  `class="hl"` to exactly those ids; no text under 14 units; a long name wraps and ends in `…`
  with a `<title>`; `--prefix` prefixes every marker id; an unknown plane exits 2 and prints the
  plane list; two runs give byte-equal output.
- `test_bpmn_label.py`: one case per row of the resolution table; a second run changes nothing;
  a cite on a blank line exits 1 and names the cite.
- `test_bpmn_check.py`: the fixture page passes; one mutation per condition fails with the
  expected line — a plane's SVG removed; a sub-process's cites removed, then passes again once
  its name is in `p.not-covered`; a label edited by hand; a `data-id` that is not in the file.
- `test_verify.py`: the `bpmn:` line is `none` for the existing page fixtures and `ok` for the
  BPMN fixture page; the line count of each rung rises by one.
- `test_page_template.py`: the new CSS rules exist and set no size under 14 px.
- `test_rung_drift.py`: the three new commands appear in `page.md`'s verify list.

## 4. Scope and acceptance

In: `scripts/bpmn.py`; `verify.sh`; the page template CSS; `rungs/page.md` (section plan,
diagram pattern, cites, verify list); `rungs/lesson.md` (plan step 2) and
`lesson/review-page.md` (one check); tests and fixtures; `SKILL.md` where it lists scripts.

Out: DMN rendering (the decision table stays hand-written HTML); clips from DI; hover-to-highlight
between a cite and the diagram; translation of names; diagram files other than `.bpmn`.

Acceptance: `/explain /Users/valukin/work/aos --as lesson` once more. The page shows the eleven
planes; each stage section explains its inner sub-processes; every BPMN cite reads as a name;
`verify.sh` prints seven `ok` lines; a cold reviewer with the new check finds no sub-process
without a paragraph. That run is the test case. Its findings feed a fold-back only when they are
faults of the skill.

## 5. Decisions

- Scope is the skill, not the delivered lesson (user, 2026-10-06).
- The picture is the file's own DI, rendered by the skill, not a hand-drawn or a bpmn-js render
  (user, 2026-10-06). bpmn-js was rejected: an npm dependency and a Chrome step for a page rung
  that has no build step, and its output would still need restyling, labels and the check.
- Coverage: deep stage sections with a mechanical check, not one section per sub-process and
  not a steps player (user, 2026-10-06).
- Cites keep their verbatim snippet and gain a generated label; the author never types a label
  (user, 2026-10-06).
