# explain: onboarding rules, Mermaid flows and the `onboard` rung

Date: 2026-10-16. Status: draft, builder check done 2026-10-16 (its four questions are settled in
section 14, items 9 to 12). The user skipped the brainstorming questions ("ok"), so every call in
this document is the author's; section 14 lists the ones to check. Coverage: not opted in.

## 1. Problem

The user, after the diadoc + esb course of 2026-10-14: the course and lesson rungs "oversimplify too
many flows". They asked for "onboarding rules for services, like exploring architecture, flows, and
so on, using text-like diagrams for visual representation, maybe mermaid".

Where the simplification happens today, read from that course run:

- The map of a source (`course/map-task.md`) is a flat list of facts in six sections. The esb map
  has 126 fact lines, among them the four preprocessor phases, the place routing, the legacy path,
  the XSLT and validator steps and the response strategy. No fact says what follows what. The
  orchestrator rebuilds the flow from the bag of facts and keeps the straight line: 20 hops of one
  sentence each, `classify, parse, route, bridge, deliver`. The branches that the map holds (the
  cross-place strategy, the legacy reply, the `To/@System` shortcut, the validator) are gone before
  the plan exists.
- A course follows one message. Every other flow of a service drops into one line of
  `not_covered` ("The template, cancel and partner requests of the service") with no evidence and
  no diagram. The user cannot see what was dropped.
- A lesson "holds one subsystem with two to four moving parts". Its first diagram is a hand-drawn
  SVG flow of boxes from left to right (`page.md` section 4). Every box costs layout work in
  `viewBox` units, so the author draws few boxes, and a condition becomes a sentence instead of a
  branch.
- Nothing mechanical finds an entry point that the map left out, a branch that the plan flattened,
  or a flow that no lesson and no `not_covered` line names.

## 2. Goals, non-goals, anti-goals

Goals:

- One written procedure, the onboarding rules, that tells a subagent how to explore one service:
  its shape, its architecture, every entry point, every flow with every branch, its state, formats,
  config, error paths and other systems. The procedure is the same whether a course maps a source
  or the user onboards to one service.
- The map that the procedure writes holds flows as Mermaid diagrams (text), with one cited fact per
  node. A branch in the code is a branch in the diagram.
- A mechanical floor: a script finds the entry points of a service by pattern, and the map must
  account for each one (traced, not traced with a reason, or dismissed with a reason). A script
  checks the map: sections, diagrams, node facts, cites and the inventory.
- Mermaid diagrams render to inline SVG in the explain pages, with the page palette, through the
  same headless Chrome that `verify.sh` uses. A reader never needs Mermaid in the browser. The
  SVG never passes through the author's context.
- The course plans from the flows: each hop names the flow it comes from, and each flow of each
  map is either on a hop or in `not_covered`, checked by `course.py check`.
- A lesson's first diagram is the flow of its hops as the map draws it, with every decision node.
- A new rung, `/explain <service-dir> --as onboard`, builds one page for one service from its map:
  the onboarding page.

Non-goals:

- No change to the lesson build (clips, gates, drop rules), the hub layout, the discovery script's
  search, or the video pipeline.
- No Mermaid in the browser at reading time. No CDN, no build step for the reader.
- No new review gate. `--review` has no effect on `onboard`.
- Sequence diagrams, class diagrams and the other Mermaid types are not checked and not required.
  Two types carry the rules: `flowchart` and `stateDiagram-v2`.
- No generated page from the map. The author writes the onboarding page from the page template, as
  every other rung does; the scripts render the diagrams into it and check it.

Anti-goals (a failure even if it runs):

- A map that lists facts and no flow. A flow diagram with a node that cites nothing.
- An entry point that the inventory found and the map does not mention.
- A course plan that drops a flow silently. Each dropped flow is named, by id, in `not_covered`.
- A lesson diagram with fewer branches than the map flow between the same two nodes.
- A page that needs the network, or an SVG with HTML labels (`foreignObject`), which the font
  guard and the PNG snapshots cannot read reliably.

## 3. Command

`/explain <service-dir> --as onboard`

- Only `--as onboard` selects the rung. It is never chosen from the content.
- The subject is one directory. A file, `this` or a topic is an error: print the rung line, say that
  the onboard rung takes one directory, offer `page`, stop.
- `--review` prints `--review: no effect on onboard` (the rule of `SKILL.md`, Contract, step 2).
- The language is `en` or `ru`, by the rule of the page rung.
- Rung line: `Rung: onboard (forced) — <reason> — subject: <path> (directory)`.

The course command does not change. Its map step follows the onboarding rules (section 10).

## 4. Output directory

`~/karpathy/out/YYYY-MM-DD-HHMMSS-onboard-<slug>/` (convention 5 of `SKILL.md`, rung `onboard`).

| Path | Holds |
|---|---|
| `map.md` | The onboarding map (section 6). The source of truth of the page. |
| `inventory.txt` | The entry points that `onboard.py inventory` found. |
| `diagrams/<id>.mmd` | One Mermaid diagram, copied verbatim from a fenced block of the map. |
| `diagrams/<id>.svg` | Its render, written by `mermaid_svg.py`. |
| `index.html` | The onboarding page, meta `<meta name="explain-rung" content="onboard">`. |
| `page.png`, `narrow.png`, `review/` | The snapshots, as for a page. |

A course keeps `map/<source-id>.md` as today, plus `map/<source-id>.inventory.txt`. A course
renders no map diagram; the lessons render the diagrams that they use (section 11).

## 5. The onboarding rules

`rungs/onboard.md` holds them, in a section "Explore the service" that `course/map-task.md` names
(as `lesson-task.md` names sections of `lesson.md`). The rules, in the order of the work:

1. Shape first. Read the build files, the main config and the entry of the process. Write one fact
   each for: the language and build tool, the runtime kind (web server, consumer, scheduler, batch,
   library), the deploy artifact (image, jar, binary, chart), and the purpose in one sentence.
2. Inventory. Run `onboard.py inventory <source-dir> --root <root>` (section 7). Read its lines.
   This is the list of entry points that the map must account for. The script finds patterns, not
   truth: a line can be a false hit, and a real entry point can be missing. Add the ones you find
   by reading. Dismiss a false hit with a reason.
3. Architecture. One `flowchart LR` of the parts at runtime: the components inside the service
   (listeners, controllers, services, repositories, clients, schedulers, by their real names), each
   store (table, cache, file system, queue the service owns), and each other system. Draw an edge
   for each call or message between them. One cited fact for each node. Keep it to the parts that a
   message meets; a utility class is not a part.
4. Flows. One flow for each entry point, or for each group of entry points that take the same
   path (name the group by the shared path; list each entry point under it). Trace the flow from
   its entry to each exit: a reply, a message sent, a row written, a log line and stop. Draw it as
   a `flowchart TD`. The rules of a flow:
   - A branch in the code is a branch in the diagram: each `if`, `when`, `switch`, strategy
     choice, `catch`, retry loop, timeout and feature flag on the path is a decision node with one
     edge for each outcome, labelled by the condition. An exit that is an error is a node.
   - Each node has one cited fact under the diagram (section 6). The cite of a decision node is
     its condition line. The cite of a call node is the call line.
   - A node that calls another system names the system and the handle (queue, endpoint, table).
   - At most 25 nodes in one diagram. A longer flow splits: the parent flow shows the stages as
     nodes, and each stage is a flow of its own with the id `<flow>-<stage>`.
   - Where a call enters a method that another flow already drew, draw one node that names that
     flow (`see <flow-id>`), not the nodes again.
5. State. The entities a message changes, and each status field with its transitions, as a
   `stateDiagram-v2`. One cited fact per state, from the line that sets it. `none found` when the
   service keeps no state.
6. Formats and transforms, routing config, error paths and other systems, as the course map asks
   today, as fact lines. The error paths section lists each retry, dead letter, timeout, error
   reply and compensation once more, as a list: the flows show where, the list shows what.
7. Not covered. Each directory or module of the source that you did not read, one line, with the
   reason. The map tells what it does not know.

Reading rules that stay from `map-task.md`: read the source only, change nothing, run no build and
no test, cite only a line read from disk, never copy a secret into a snippet, use CodeGraph first
when `.codegraph/` exists, `grep -rn` for a name.

Section 15 adds the keyed `Shape` lines, the `Conventions` and `Where to look` sections and the
rules of their facts; the rung file holds them as rules 1 and 7.

Reading budget: the rules do not cap the lines read. They cap what leaves the map: an entry point
in the inventory that has no line in `Entry points` fails the check. A reason to not trace a flow
is one sentence that names the flow with the same shape ("the same path as `send`, with the
`cancel` type") or says why it is off any message path ("the admin health endpoint reads no
message").

## 6. The map

One Markdown file. The level-2 sections, in this order, all present (`none found` as the one line
of an empty section):

```
# Map: <id>

## Shape
- <key>: <fact> | <path>:<line> | <snippet>

## Architecture
```mermaid
flowchart LR
  ...
```
- <node-id>: <fact> | <path>:<line> | <snippet>

## Entry points
- <kind> <name> -> <flow-id> | <path>:<line> | <snippet>
- <kind> <name> -> not traced: <reason> | <path>:<line> | <snippet>
- <kind> <name> -> not an entry point: <reason> | <path>:<line> | <snippet>

## Flows
### <flow-id>: <question>
```mermaid
flowchart TD
  ...
```
- <node-id>: <fact> | <path>:<line> | <snippet>

## State
```mermaid
stateDiagram-v2
  ...
```
- <state>: <fact> | <path>:<line> | <snippet>

## Formats and transforms
## Routing config
## Error paths
## Other systems
- <system>: <handles> | <path>:<line> | <snippet>

## Conventions
- <topic>: <fact> | <path>:<line> | <snippet>

## Where to look
- <task>: `<path>` | <path>:<line> | <snippet>

## Not covered
- <directory or module>: <reason>
```

Rules of the format, which `onboard.py check` enforces (the rules of `Shape`, `Conventions` and
`Where to look` are in section 15):

- A fact line is `- <fact> | <path>:<line> | <snippet>`. `<path>` is relative to the root. The
  snippet has at most 12 words, copied verbatim from that line (the cite rules of convention 2).
  `Not covered` lines carry no cite.
- A node fact line starts with the node id and a colon: `- <id>: <fact> | ...`. Every node of the
  diagram above it has exactly one such line, and every such line names a node of that diagram.
- Ids: a flow id and a node id match `[a-z][a-z0-9_-]*`. Node ids are unique inside one diagram.
  A subgraph id is not a node.
- A diagram is one fenced block with the info string `mermaid`. The first line of the block is
  `flowchart TD`, `flowchart LR` or `stateDiagram-v2`. `Architecture` holds one `flowchart`.
  Each `### <flow-id>: <question>` under `Flows` holds one `flowchart`. `State` holds one
  `stateDiagram-v2` or the line `none found`. In a `stateDiagram-v2`, each state that is not
  `[*]` has one fact line, keyed by the state name.
- A flowchart has at most 25 nodes.
- `Architecture`, `Flows` and `State` may hold the one line `none found` when the source has no
  code to trace: a docs repository, a config repository. A docs source that documents a request
  sequence (an API guide with "send, then poll") draws it as a flow; its node cites point to the
  lines of the docs. The check accepts `none found` in these three sections and then applies no
  diagram rule to them.
- The `<kind>` of an `Entry points` line is one of the five kinds of the inventory (section 7):
  `http`, `listener`, `route`, `schedule` or `main`.
- An `Entry points` line ends its fact part with `-> <flow-id>`, `-> not traced: <reason>` or
  `-> not an entry point: <reason>`. A named flow id exists under `Flows`. A reason is not empty.
- With `--inventory <file>`, every `<path>:<line>` of the inventory is the cite of one
  `Entry points` line.
- `Other systems` keeps the shape that `course_discover.py` reads: handles in backticks in the fact
  part. The section title does not change.

The map is for the orchestrator and the author, not for a reader. Its prose is not linted. Code
names stay in backticks.

## 7. `scripts/onboard.py`

Two commands. Each prints one line per finding and one summary line last.

`onboard.py inventory <source-dir> --root <root> [--out <file>]`: greps the source for entry-point
patterns and prints one line per hit, `<path>:<line>\t<kind>\t<text>`, path relative to
`<root>`, text the line with the white space squashed, at most 120 characters. Writes the same
lines to `--out`. Skips test trees (`src/test`, `test/`, `tests/`, `*_test.go`, `*Test.java`,
`*Test.kt`, `*Spec.kt`), `node_modules`, `target`, `build`, `.git`, `vendor`. Exits 0 with
`inventory: <n> entry points`, 2 on a missing directory.

The patterns, by kind (the script holds the table; the rung file lists the kinds):

| Kind | Patterns |
|---|---|
| `http` | `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping`, `@RequestMapping` on a method, `@Path(` (JAX-RS), `@MessageMapping`, `@ServerEndpoint`; Go: a router call with a route string literal as its first argument, `\.(Get\|Post\|Put\|Delete\|Patch\|GET\|POST\|PUT\|DELETE\|PATCH\|Handle\|HandleFunc)\(\s*"`, and `http.HandleFunc(`. The literal anchor keeps a Go service from producing hundreds of hits that each need a dismissal line. |
| `listener` | `@JmsListener`, `@RabbitListener`, `@KafkaListener`, `@KafkaHandler`, `@SqsListener`, `@StreamListener`, `@ServiceActivator`, `@InboundChannelAdapter`, `@EventListener`, `@TransactionalEventListener`, `@ExternalTaskSubscription`, `implements JavaDelegate`, `: JavaDelegate`; Go: `.Consume(`, `NewReader(`, `NewConsumer(`, `Subscribe(` |
| `route` | Camel: `from(` inside a `RouteBuilder`, `- from:` and `uri:` under `from` in `*.camel.yaml`, `routeTemplate`; `@GrpcService`, `Register` + `Server(` (Go gRPC) |
| `schedule` | `@Scheduled`, `cron.`, `NewTicker(`, `time.Tick(` |
| `main` | `public static void main`, `fun main(`, `func main(` |

Languages: Java, Kotlin, Go, plus YAML and XML route files. Nothing else in this version; the table
is one dict and grows by a row.

`onboard.py check <map.md> --root <root> [--inventory <file>]`: checks section 6. One failure per
line, then `onboard: ok` or `onboard: <n> failures`. Exit 0, 1, or 2 for an unreadable map or
root. The prefix of a line tells where the fault is:

| Prefix | Meaning |
|---|---|
| `section: missing <title>` / `section: <title> out of order` | The level-2 skeleton. |
| `diagram <where>: none` / `diagram <where>: not flowchart or stateDiagram-v2` / `diagram <where>: <n> nodes, more than 25` | `<where>` is `architecture`, `state` or the flow id. |
| `node <where>/<id>: no fact line` / `fact <where>/<id>: not a node` / `fact <where>/<id>: two lines` | Node and fact lines. |
| `cite <section>#<n>: <problem>` | The problems of `cite_check`: path missing under root, line beyond the end, snippet not on that line, more than 12 words. Reuse `_cite_problems` of `course.py` (move it to `cite_check.py` if the import is awkward). |
| `entry #<n>: unknown kind <kind>` / `entry #<n>: no flow id and no reason` / `entry #<n>: flow <id> not in Flows` | Entry lines. `<kind>` is the first word of the fact, or `none` when the fact is empty. |
| `inventory <path>:<line>: not in Entry points` | Only with `--inventory`. |
| `shape: missing <key>` / `shape: <key> twice` / `shape #<n>: unknown key <key>` / `shape #<n>: no command in backticks` | The keyed `Shape` lines (section 15). |
| `conventions: missing <topic>` / `conventions #<n>: no topic` | The `Conventions` lines (section 15). |
| `where: missing <key>` / `where #<n>: no path in backticks` / `where #<n>: <path> not under root` | The `Where to look` lines (section 15). |
| `map: cannot read` | Not a Markdown file with a `# Map:` title. Exit 2. |

The Mermaid parser is small and tolerant: it needs node ids and a count, not a full grammar.
Strip edge labels (`|...|`, `-- text -->`, `-. text .->`), split on arrows, and take the
`[a-z][a-z0-9_-]*` token at the start of each segment, before any shape bracket (`[`, `(`,
`{`, `>`), as a node id. `subgraph <id>` and `end` lines are not nodes. In a `stateDiagram-v2`,
a state is a token on either side of `-->` or after `state`, not `[*]`.

## 8. `scripts/mermaid_svg.py`

Renders Mermaid text to SVG in headless Chrome, with the Chrome handling of `verify.sh` (process
group, poll the dump for `</html>`, kill, sweep by the temp path).

```
mermaid_svg.py render <in.mmd> [<out.svg>]     one diagram; stdout when no out path
mermaid_svg.py inline <index.html>             every figure.mermaid of the page (section 9)
env EXPLAIN_MERMAID_JS   the bundle (default $HOME/karpathy/video-workspace/mermaid/mermaid-12.2.0.min.js)
env MERMAID_TIMEOUT      seconds to wait for Chrome (default 60)
exit 0 ok, 1 a render failed, 2 usage or Chrome not found
```

The bundle: `mermaid@12.2.0`, file `dist/mermaid.min.js`, 5 494 801 bytes, sha256
`a8a6a6f805b074a8261a2825c86f99c8054acb3b35f50bb7e24a4f9f2c3c3b9f`. When the file is missing,
the script prints `mermaid: download mermaid-12.2.0.min.js (5.5 MB)`, fetches
`https://unpkg.com/mermaid@12.2.0/dist/mermaid.min.js` (fallback
`https://cdn.jsdelivr.net/npm/mermaid@12.2.0/dist/mermaid.min.js`) to `<name>.<pid>.part`,
checks the hash, and moves it into place, by the fetch rules of `video-workspace.sh`. A wrong hash
is `mermaid: FAIL sha256 <got>`; the part file is removed. The file lives beside the video
workspace but needs none of it: no `npm ci`, no Remotion.

The render: one harness HTML in a temp dir, the bundle inlined in a `<script>`, then a script
that calls `mermaid.initialize(config)` and `mermaid.render(id, text)` for each diagram, puts the
SVG in `<div id="out-<n>">`, and sets `data-mermaid="OK"` or `FAIL <n>: <message>` on `<html>`.
Chrome runs with `--headless=new --disable-gpu --dump-dom --hide-scrollbars`. One Chrome run for
all the diagrams of a page. The spike of 2026-10-16 measured 1.0 s for a flow of 11 nodes.

The config is fixed in the script (no option): `theme: "base"`, `securityLevel: "strict"`,
`htmlLabels: false` at the top level and under `flowchart` (so every label is SVG text and the
SVG holds no `foreignObject`), `fontSize: "14px"` (the font floor of the page), and
`themeVariables` from the palette of `templates/page.html`: `fontFamily` the `--sans` stack,
`primaryColor #f0eee6`, `primaryTextColor #1f1d1a`, `primaryBorderColor #1f1d1a`,
`lineColor #1f1d1a`, `secondaryColor`, `tertiaryColor`, `background` and `edgeLabelBackground`
`#faf9f5`. A diagram id is the stem of its `.mmd` file, and the SVG element id is `mmd-<stem>`;
Mermaid scopes its `<style>` by that element id, so two diagrams on one page never share a rule,
and a rule never reaches a section of the page whose id equals the stem (`section#flow-auth`
beside `flow-auth.mmd`: the live run of 2026-10-17 lost its paragraph gaps to `#flow-auth p`
before the prefix existed).

What the script does to the SVG before it writes it: keeps `viewBox`; sets `width` and `height`
to the `viewBox` size rounded **up** to whole pixels, so the SVG keeps its intrinsic size and never
scales (the font guard of the page multiplies the font size by rendered width over `viewBox`
width; a width rounded down gave `SMALLTEXT:14` and failed, measured 2026-10-16; rounded up, both
viewports pass); removes the root `style="max-width: …"`; replaces Mermaid's
`role="graphics-document document"` with `role="img"`; adds `data-ste="skip"`,
`aria-labelledby="<id>-title"` and a `<title id="<id>-title">` with the text that `inline` takes
from the figcaption (for `render`, from `--title`, default the id).

Failure lines: `mermaid: FAIL <id> <message>` with Mermaid's parse message, `mermaid: FAIL Chrome
not found <path>`, `mermaid: FAIL timeout`. Last line on success: `mermaid: ok <n> diagrams`.

## 9. The Mermaid pattern of a page

`rungs/page.md` section 4 gets one more pattern, and `templates/page.html` one CSS rule.

```html
<figure class="mermaid" data-src="diagrams/<id>.mmd">
  <figcaption>One STE sentence: what this flow is.</figcaption>
</figure>
```

- Write the diagram text to `diagrams/<id>.mmd` in the output directory. Then run
  `python3 <skill-dir>/scripts/mermaid_svg.py inline index.html`. It renders each `.mmd` to
  `diagrams/<id>.svg` and writes the SVG as the first child of its figure, before the
  `figcaption`. A second run replaces the SVG. Never paste an SVG by hand.
- CSS, three rules: `figure.mermaid` takes the rules of `figure.bpmn` (breaks out of the column,
  `overflow-x: auto`), `figure.mermaid svg { display: block; max-width: none }`, and
  `figure.mermaid svg text { font-size: 14px }`. The third is needed because the template's
  `svg text { font-size: 18px }` wins over the size that Mermaid's labels inherit, as it did for
  BPMN (`svg.bpmn text`). The SVG keeps its intrinsic size at every viewport: a diagram wider
  than the column scrolls inside its figure, as a BPMN plane does. A `flowchart TD` of 11 nodes
  measured 496 px wide, so a TD flow usually fits the 500 px viewport with a small scroll; a
  `flowchart LR` scrolls. The 25-node cap is a reading cap, not a layout cap.
- When to use it: any flow with a branch, and any state machine. The hand-drawn flow pattern stays
  for a straight pipeline of at most six boxes. The sequence and layers patterns stay. A BPMN plane
  keeps its own pattern.
- The cites of the figure's section go in the `div.cites` after the lead paragraph or the
  figcaption, as for a diagram-only section today.
- The `media` check of `verify.sh` does not read `data-src`. An empty figure is a fault that
  `mermaid_svg.py inline` reports (exit 1 when a `data-src` file is missing) and that the tiles
  show.

### 9.1 The onboarding page

The author writes `index.html` from `templates/page.html` by the rules of `page.md` ("Fill the
template", "Provenance", "Write the prose", "Verify and export"), with this section plan in place
of "Plan the sections". The section count follows the flows, as it follows the planes of a BPMN
subject: never merge flows to get under twelve sections.

- Title: what the service does and why it exists, as a question. Answer box: the purpose, the
  runtime kind and the main flows by name, two to four sentences, from `Shape`.
- `#whole`, "What is <service> made of?": a lead paragraph, the architecture diagram
  (`diagrams/architecture.mmd`, the block of the map verbatim), then one paragraph for each other
  system and each store that the diagram shows.
- `#entry`, "Where does a message enter?": a table (`.table-wrap > table`) with one row per
  `Entry points` line of the map that is traced or not traced: kind, name, the flow as a link to
  its section, or "not traced" with the reason. Dismissed inventory lines stay in the map only.
- One section per flow, id `flow-<flow-id>`, `<h2>` the question of the flow: a lead paragraph
  (what comes in, what leaves), the flow diagram (`diagrams/flow-<flow-id>.mmd`, verbatim), then
  one paragraph for each decision node that names its branches and says why the branch exists,
  and one paragraph for each node that calls another system or writes a store. A node that says
  `see <flow-id>` gets one sentence with a link to that section.
- `#state`, "Which states does a message go through?": the state diagram and one paragraph per
  state. Omit the section when `State` is `none found`.
- `#formats`, `#config`, `#errors` and `#systems`: reference sections from the four fact sections
  of the map. Exact rules go into `details.walk`. `#errors` is a list: each retry, dead letter,
  timeout and error reply, with a link to the flow section where it happens. `#systems` is a table
  of system and handles.
- `#terms`: the glossary, by the page rule.
- Section 15.4 adds `#run`, `#conventions` and `#where` to this plan.
- `Not covered` in the footer: each `Not covered` line of the map, and each not-traced entry
  point with its reason.
- Every section holds at least one `<cite>` (a directory subject). The cites are the map lines,
  copied; `cite_check.py` verifies them again on the page.
- Provenance as for a directory subject: `data-kind="directory"`, `data-root` the repo root.
- No steps player is required. The line `<n> sections would gain from a clip` is not printed.

## 10. The course: map step

`course/map-task.md` becomes a short prompt that points at `rungs/onboard.md`: "Explore the
service" and "The map", with the course overrides (the ids, the root, the output path
`{course_dir}/map/{source_id}.md`, the inventory path `{course_dir}/map/{source_id}.inventory.txt`,
the language). The placeholders stay the set of today. The result line stays
`map: done {source_id} <n> facts` (`<n>` counts the fact lines, node lines included) or
`map: failed <reason>`.

The map subagent runs `onboard.py inventory` first and `onboard.py check --inventory` last, and
fixes the map until `onboard: ok`, by a stop rule of 3 rounds. If failures remain, it still ends
with `map: done` and lists the failure lines before it; the orchestrator prints them.

`rungs/course.md` "Map the sources": after the subagents return, the orchestrator runs
`onboard.py check <map> --root <root>` on each map and prints the failure lines. A map with
failures still counts as a map: it is an input, not the artifact. Only a map that the check cannot
read (`map: cannot read`) counts as `map: failed`. A map whose `Flows` is `none found` is a map:
a docs or config source has no flow to trace, and its facts still support hops.

Discovery does not change: `course_discover.py` reads `Other systems` as today.

## 11. The course: plan and lessons

`course.json` gets two fields on a hop. `"flow": "<source-id>/<flow-id>"` names the flow that the
hop comes from: required for a `code` hop, a string or `null` for a `docs` hop (a docs map can
have no flow), `null` for an `inferred` hop. The named flow is a `### <flow-id>:` heading under
`Flows` in `map/<source-id>.md`. `"nodes": ["<node-id>", …]` lists the nodes of that flow that
the hop covers, in flow order: non-empty when `flow` is a string, `[]` when it is `null`.

`from` and `to` of a hop do not change: they name systems, and the hub prints them in each box.
The binding of a hop to the flow is `nodes`, and it is checked.

`course.json` becomes version 2. `course.py` refuses a version 1 file with one line,
`course: version 1 is older than this skill; start a new course`, exit 2, from every command. A
course of `out/` is discardable output; nothing migrates it.

Planning rules added to "Plan the course":

- Read the `Flows` of each map. The flows that carry the message of the course give the hops. Walk
  the nodes of such a flow in their order. A node that changes the message, sends it, stores it, or
  replies is a hop, together with the nodes before it since the last hop. A decision node whose
  edge leads to an error exit gives a `branch` hop. A decision node that splits the main path gives
  one hop for each edge, and `what` names the condition.
- A flow that some hop names is a followed flow. Every node of a followed flow is in the `nodes`
  of one hop, or named in `not_covered` as `<source-id>/<flow-id>/<node-id>`. Thus a node leaves
  the course only by name.
- A flow of a map that no hop names gets one sentence in `not_covered` that holds
  `<source-id>/<flow-id>`. A sentence can name several flows or nodes.

Checks added to `course.py check` (the Mermaid parser of `onboard.py` reads the maps):

| Line | Meaning |
|---|---|
| `hop <id>: flow <source>/<flow> not in map/<source>.md` | The map has no such flow heading. |
| `hop <id>: flow missing` | A `code` hop with no flow. |
| `hop <id>: nodes empty` / `hop <id>: node <n> not in flow <source>/<flow>` | The node binding. |
| `flow <source>/<flow>: in no hop and not in not_covered` | The flow floor, for every flow of every map of a source of the course. |
| `node <source>/<flow>/<id>: in no hop and not in not_covered` | The node floor, for every node of a followed flow. |

`summary` prints the flow and the node count after the evidence of a hop:
`code, flow esb/request, 4 nodes`.

`course/lesson-task.md` gets one override under "Scope": the first diagram of the lesson uses the
Mermaid pattern of `page.md`. Its text is cut from the map block of the flow by the `nodes` of the
hops of the lesson: every line of the block whose node ids are all in that set, plus each edge
that leaves the set, with its far node kept as one node that names the lesson that covers it. The
cut is mechanical; nothing is redrawn. Each decision node of that diagram gets one paragraph that
names its branches, or its own section. The lesson still holds "two to four moving parts": a
moving part is a hop, not a node.

A rule for the plan: a lesson holds the hops of one flow, or of two flows that meet at one node.

## 12. `SKILL.md`, `verify.sh`, `README.md`

- `SKILL.md`: `onboard` in the argument-hint, the syntax line and step 4 of the Contract ("eight
  names"); a row in the rung table (forced only, "A service to onboard to: its architecture and
  every flow"); a bullet under the rung rules (English or Russian); a bullet under Rung files; the
  conventions sentence lists seven artifact rungs.
- `verify.sh`: `rung=onboard` renders the two page viewports; the usage message lists it. No new
  check line: the page keeps the page lines (six) and `bpmn` last.
- `scripts/bpmn.py`: `onboard` joins `RUNGS`, else `bpmn.py check --rung onboard` exits 2 and
  every onboard page fails with `bpmn: FAIL bpmn exit 2`.
- `README.md`: the `--as` list, one clause for the rung.

## 13. Files and tests

New: `rungs/onboard.md`, `scripts/onboard.py`, `scripts/mermaid_svg.py`,
`tests/test_onboard.py`, `tests/test_mermaid_svg.py`, test fixtures (a small map, a small Java and
Go tree for the inventory, a `.mmd` pair).

Changed: `SKILL.md`, `README.md`, `rungs/page.md`, `rungs/course.md`, `course/map-task.md`,
`course/lesson-task.md`, `templates/page.html`, `scripts/course.py`, `scripts/verify.sh`,
`scripts/bpmn.py` (`RUNGS`), `tests/test_course_prompts.py` (the section list of the map),
`tests/test_course.py` (the `flow` and `nodes` fields, the two floors), `tests/test_rung_drift.py`
(eight names, the new rung bullets, the section plan of 9.1), `tests/test_verify.py` (the onboard
rung renders two viewports), `tests/test_bpmn_check.py` (the rung list), `tests/test_page_template.py`
(the three `figure.mermaid` rules).

Tests that need Chrome (`mermaid_svg.py render`, `inline`, the onboard verify case) run in the
normal suite, as the `verify.sh` tests do today. They read the real bundle from
`EXPLAIN_MERMAID_JS` or its default path, and they skip with the message
`mermaid bundle missing: <path>` when it is absent; no test of the normal suite fetches the
network. The bundle is in place on this machine (2026-10-16, hash checked). The download path
of the script is tested by one gated test (`EXPLAIN_MERMAID_E2E=1`) that fetches into a temp
directory and checks the hash, and by one normal test that serves a wrong file from a local
path and expects `mermaid: FAIL sha256 <got>`.

Proof at the end: run `/explain <one real service> --as onboard` on a repo of the user (a qmd
collection such as `diadoc`), read the tiles, and compare the entry points of the map with the
inventory. Then resume nothing: the diadoc + esb course of 2026-10-14 is not rebuilt.

## 14. Calls made by the author (check these)

1. A new rung `onboard` exists, besides the course change. Reason: the rules need one owner, and a
   single service is the case the user names ("onboarding rules for services").
2. Mermaid is the notation in the map and in the pages, rendered to SVG at build time by headless
   Chrome; the reader's page holds the SVG only. Reason: convention 3 (offline, no CDN); the font
   guard and the PNG tiles read SVG text; the author draws a 25-node branching flow in text with no
   layout work, which is what removes the pressure to flatten.
3. The bundle is `mermaid@12.2.0`, fetched once by hash into the video workspace directory, not
   added to `video/package.json`. Reason: `npm ci` plus the browser download is 700 MB for one
   5.5 MB file, and the onboard rung must not need Remotion.
4. Two diagram types carry the checks: `flowchart` and `stateDiagram-v2`. Reason: node facts need a
   stable notion of a node.
5. The entry-point inventory covers Java, Kotlin and Go, plus Camel YAML. Reason: the user's
   stack (memory: JUnit XML and `go test -json`, no other ecosystems unless asked).
6. The map is not linted (it is for agents); the page is. The onboarding page is written by the
   author from the page template, not generated from the map. Reason: every rung works this way,
   and a generator is the one piece that this design can leave out.
7. The course hub does not render the maps' diagrams. Reason: scope. The flows that the course does
   not follow are named by id in `not_covered`; the maps stay on disk beside the hub.
8. A map with check failures is still an input to the course. Reason: dropping a whole source over
   one bad snippet loses more than it protects.

After the builder check (2026-10-16), four more:

9. The SVG keeps its intrinsic size, rounded up to whole pixels, and scrolls inside its figure;
   `figure.mermaid svg text` is 14 px. Reason: measured against the font guard of the template
   (section 8). A scaled SVG fails `render 500x844` with `SMALLTEXT`.
10. The onboarding page has a fixed section plan with one section per flow and no merging
    (section 9.1). Reason: merging flows into one section is the flattening that the user named.
11. A docs or config source writes `none found` under `Architecture`, `Flows` and `State`, and its
    facts still support `docs` hops; `flow` is required for `code` hops only. Reason: the
    diadoc + esb course had `kontur-docs` as a docs source cited by two hops.
12. A hop binds to its flow by `nodes`, checked against the map, and every node of a followed flow
    is on a hop or in `not_covered` by name. `from` and `to` stay system names. Reason: the hub
    prints `from → to`; a node-level floor is what makes "no branch dropped" checkable.

## 15. Follow-up of 2026-10-18: run, conventions, where to look

The user read the `codebase-onboarding` skill of the ecc repository (affaan-m/ecc) and asked what to
take. Four things: the commands to build, test and run the service; the framework versions; the
conventions of the code, each with an example; and a "where to look" table from a task to a place.
The rest of that skill is covered by the map in a stricter form, and its starter `CLAUDE.md` output
is out of scope. These rules extend sections 5, 6, 7 and 9.1. The ids and prefixes here are
authoritative where the earlier sections are silent. A map written before 2026-10-18 fails the check
by design (`shape #<n>: unknown key`, `section: missing Conventions`). It is rewritten, not
grandfathered.

### 15.1 `Shape` lines carry a key

Each `Shape` line is `- <key>: <fact> | <path>:<line> | <snippet>`. The keys, in this order:

| Key | Fact | Required |
|---|---|---|
| `language` | The language and the build tool. | yes, once |
| `framework` | One framework or runtime library and its version, from the line that pins it (`pom.xml`, `build.gradle.kts`, `go.mod`). | no, any number |
| `runtime` | The runtime kind: web server, consumer, scheduler, batch or library. | yes, once |
| `artifact` | The deploy artifact: image, jar, binary or chart. | yes, once |
| `purpose` | The purpose of the service, one sentence. | yes, once |
| `build` | The command that builds it, in backticks. | yes, once |
| `test` | The command that runs its tests, in backticks. | yes, once |
| `run` | The command that runs it locally, in backticks. | yes, once |

The cite of a command is the line that defines it: a Makefile target, a Gradle or Maven plugin line,
a `scripts` entry, a README line, a Dockerfile `ENTRYPOINT` or `CMD`, or a CI job line. When the
source has no such command (a docs repository, a library with no entry), the line is
`- build: none found` with no cite; the same for `test` and `run`. The fact of `build`, `test` and
`run` holds one command in backticks (the `HANDLE` pattern of `Other systems`). The check:

- `shape: missing <key>` for each required key with no line;
- `shape #<n>: unknown key <key>` for a line whose key is not in the table, or a line with no key;
- `shape #<n>: no command in backticks` for `build`, `test` or `run` that is neither `none found`
  nor a fact with a backticked handle.

A key other than `framework` that appears twice is reported as `shape: <key> twice`.

`Shape` has no other key. A fact of another subject goes in its own section: a port, a queue name or
a URL in `Routing config`, a retry in `Error paths`, a pipeline or a registry in `Other systems`.
Each line holds one fact, and its cite shows that fact.

### 15.2 `Conventions`

A new level-2 section after `Other systems`. Each line is `- <topic>: <fact> | <path>:<line> |
<snippet>`: one convention of the code with one example line as its cite. Four topics are required;
any other topic that matches the id pattern is allowed:

| Topic | What the fact says |
|---|---|
| `tests` | Where the tests live and how a test file is named, from one test file. |
| `errors` | How an error is raised and handled on a message path (an exception type, a `Result`, an error reply), from one line that does it. |
| `wiring` | How a dependency reaches a class: constructor injection, a factory, a global, from one line that does it. |
| `naming` | How the classes or packages of the message path are named (suffixes such as `Listener`, `Service`, `Repository`; one package per feature or per layer), from one declaration line. |

A topic with nothing to find is `- <topic>: none found` with no cite. The check: `conventions:
missing <topic>` for a required topic with no line, `conventions #<n>: no topic` for a line with no
`<key>:` head. Git conventions (commit style, branch names) are not in the map: the rules cite
lines read from disk only, and `git log` is not a file.

### 15.3 `Where to look`

A new level-2 section after `Conventions`, before `Not covered`. Each line is
`- <key>: `<path>` | <path>:<line> | <snippet>`: a task of a new team member, the directory or file
where that task starts, and one existing example line under that path as the cite. The keys:

| Key | Required when |
|---|---|
| `add-http`, `add-listener`, `add-route`, `add-schedule` | `Entry points` has a traced or not-traced line of that kind (`main` has no row). A `not an entry point` line counts for no kind. |
| `change-routing` | `Routing config` is not `none found`. |
| `add-transform` | `Formats and transforms` is not `none found`. |
| `add-test` | The `test` line of `Shape` is not `none found`. |
| any other key that matches the id pattern | never; allowed. |

The check: `where: missing <key>` for a required key with no line; `where #<n>: no path in
backticks` when the fact part holds no backticked handle; `where #<n>: <path> not under root` when
the first backticked handle, joined to the root, is not an existing file or directory. The path is
relative to the root and is the first text in backticks of the line. The cite rules apply as to every
fact line.

`Entry points` gets one more check: `entry #<n>: unknown kind <kind>` when the first word of the fact
is not one of the five kinds of the inventory (`http`, `listener`, `route`, `schedule`, `main`); an
empty fact reports `none`. The check runs before the flow and reason checks of the same line.

### 15.4 The page

Three sections join the plan of section 9.1, and the nav gets a link for each:

- `#run`, "How do I build, test and run it?", directly after `#whole`. A stack table
  (`.table-wrap > table`): one row per `language` and `framework` line, with the name and the
  version. Then, for `build`, `test` and `run` in this order, one sentence that says what the
  command does and a `figure.code` (the captioned code of `page.md`, "Fill the template"). Its
  `figcaption > code` holds the key (`build`, `test` or `run`), and its `pre > code` holds the
  command alone. The cites of the stack table go in a `div.cites` after the table, and the cite of
  each command in a `div.cites` after its figure, as the page does after a paragraph. A `none found`
  line becomes one sentence that says no such command was found, with no figure. Commands never sit
  inline in prose (the user's rule: code goes in a code block).
- `#conventions`, "How is the code written?", after `#systems`: one paragraph per `Conventions`
  line, each with its cite; a `none found` topic becomes one sentence. The section is omitted when
  every `Conventions` line is `none found`.
- `#where`, "Where do I look to change something?", after `#conventions` and before `#terms`: a
  table (`.table-wrap > table`) with one row per `Where to look` line: the task in words, the
  path, and the cite. The section is omitted when `Where to look` is `none found` (the rule of
  `#state`).

The answer box does not change. The rung file lists the three ids with the others in "Plan the
sections", and `test_rung_drift.py` locks them.

### 15.5 Files and tests of this follow-up

- `scripts/onboard.py`: `TITLES` gains `Conventions` and `Where to look` before `Not covered`;
  `SHAPE_KEYS`, `SHAPE_REQUIRED`, `CONVENTION_TOPICS`, `WHERE_ENTRY_KINDS`, `WHERE_KEYS` and
  `ENTRY_KINDS` (the keys of `PATTERNS`) are module constants; new
  functions `_shape_lines(doc) -> list[str]`, `_convention_lines(doc) -> list[str]`,
  `_where_lines(doc, root) -> list[str]`, called from `check_map` after `_handle_lines` and before
  `_cite_lines`. `check_map` keeps its order otherwise.
- `tests/test_onboard.py`: cases for each new prefix and for the `none found` forms; the fixture
  `tests/fixtures/onboard/map.md` and its `tree` gain keyed `Shape` lines, the two sections and the
  files they cite.
- `rungs/onboard.md`: rule 1 of "Explore the service" names the keys; a new rule 7 "Conventions and
  where to look" before "Not covered" (which becomes rule 8); the skeleton of "The map" and the
  prefix table; "Plan the sections" adds the three sections. `tests/test_rung_drift.py` follows:
  eight rules, twelve titles, ten prefixes, the three ids.
- `course/map-task.md`: no change (it names the sections of the rung file by title).
- Proof: the diadoc output of 2026-10-17 is extended by hand to the new format (keyed `Shape`, the
  two sections, the three page sections), `onboard.py check` prints `onboard: ok` and `verify.sh`
  prints all `ok`. The output stays untracked.

## 16. Follow-up of 2026-10-18: events and the event matrix

### 16.1 Problem and intent

The user onboarded to a new service that "entirely follows event stream/store pattern". The
onboarding page "gave some high level flow but didn't provide names of said events": the reader
could not take an event name seen in a log, a topic or a table and find who emits it, what it
carries, where it is stored and who reacts to it. That page came from an older version of the rung,
but the current rules have the same gap: nothing asks for events by name. The diadoc map of
2026-10-17 names its routing keys only because they happened to sit in `Routing config` and in the
flow labels; no section lists them, and no line says which component emits or consumes each one.

The intent: for an event-based service, the map holds one entry for each event with its exact name,
and the page has a matrix, one row per event and one column per component, that lets the reader
follow an event across the service by clicking.

The user agreed to the playback below and gave no further detail ("ok"). Every other call is the
author's and is listed in 16.8.

Goals:

- Each event of the service is named in the map, verbatim as the code names it (a class, a record, a
  routing key, a stream or event-type string), with a cite of the line that declares the name.
- For each event: its payload type, where it goes (event store stream, topic, exchange or
  in-process), each component that emits it and each component that consumes it, each with a cite.
  An aggregate that rebuilds its state from the event counts as a consumer.
- A gap is visible, never silent: an event emitted or consumed outside the repository says so and
  names the handle; an event with no consumer in the repository says `none found`.
- A mechanical floor: the inventory finds event-type declarations by pattern, and the map must name
  or dismiss each one, as it does for entry points.
- The page gets an `#events` section with the matrix. Each mark in the matrix links to the flow
  section where that emit or that consume happens, so the reader follows an event by clicking.

Non-goals:

- No matrix across repositories. The rung explores one service directory; an event that leaves
  the repository ends in an `outside:` line. A cross-service view is a later project (the course
  rung is the likely owner).
- No command catalog. A command shows only as the trigger in the prose of an `emits` line.
- No event choreography diagram generated from the map, and no new required diagram. `Architecture`
  and the flows stay the diagrams.
- No schema registry, Avro or protobuf parsing, and no upcaster or version tracking beyond what the
  `type` fact says in prose.
- No change to a map of a service with no events except one line: `## Events` with `none found`.

Anti-goals (a failure even if it runs):

- An event that the page names only in prose, or a flow label that holds an event name that the
  `Events` section lacks.
- A matrix mark with no cited line in the map behind it.
- An event declaration that the inventory found and the map neither names nor dismisses.
- A consumer or emitter written from a guess: every component in an `emits` or `consumes` line is
  cited at the line that publishes, applies, appends or handles the event.

### 16.2 The rule (rung file, "Explore the service")

A new rule, after rule 5 "State", numbered 6; the later rules move down by one (Formats... becomes 7,
Conventions and where to look 8, Not covered 9). Its content:

- Events. Find each event of the service: a type or a name that one part publishes, appends to an
  event store, applies, or sends to a topic or exchange, and that another part handles. Look for
  event classes and records, `apply(`/`AggregateLifecycle.apply`, event-store appends,
  `publishEvent`, `ApplicationEventPublisher`, Kafka and RabbitMQ sends with an event payload,
  routing keys and event-type strings, `@EventHandler`, `@EventSourcingHandler`, `@SagaEventHandler`,
  `@EventListener`, projection handlers and stream subscriptions. Write one entry for each event under
  `Events`, in the format of 16.3. A service with no events writes `none found`.
- The inventory lists event declarations as `event` hits (16.4). Each must be the cite of a `type`
  line or of a `not an event` line.
- A flow node that emits or consumes an event names the event, verbatim, in its fact.

### 16.3 The `Events` section of the map

A new level-2 section `Events`, after `State` and before `Formats and transforms`. `TITLES` has
thirteen entries. The section holds an optional list of dismissals, then one level-3 entry for each
event:

````
## Events
- not an event: `<Name>`: <reason> | <path>:<line> | <snippet>

### <event-name>
- type: <what names the event, in prose with code names in backticks> | <path>:<line> | <snippet>
- payload: <the payload type and its fields> | <path>:<line> | <snippet>
- stream: <where it goes: the event store stream, topic, exchange or `in-process`> | <path>:<line> | <snippet>
- emits: `<Component>` <when, in prose> [-> <flow-id>] | <path>:<line> | <snippet>
- consumes: `<Component>` <what it does, in prose> [-> <flow-id>] | <path>:<line> | <snippet>
````

Rules:

- `<event-name>` is the name exactly as the code writes it: `OrderPlaced`, `event.document.signature`,
  `order-placed.v2`. It is unique in the section. On the page it becomes the anchor `event-<slug>`,
  where `<slug>` is the name lowercased with each run of characters outside `[a-z0-9]` replaced by
  `-`.
- `type` is required, once. Its cite is the line that declares the name: the class or record
  declaration, or the constant or string that holds the routing key or event type. When the
  declaration is outside the root (a framework event such as Spring's `ApplicationReadyEvent`), the
  cite is the first line under the root that names it, and the fact says where the type comes from.
- `payload` is optional, once. It is for an event whose name is not its payload class: a routing key
  or an event-type string that carries `BoxEvent` or a generic `DomainEvent`. Its cite is the
  declaration of the payload class. When the name is the class, there is no `payload` line.
- `stream` is required, once. `in-process` is a valid fact for an application event inside one
  process.
- `emits` and `consumes` are required, one or more each. Each line is one of three forms:
  - a component: the first text in backticks is the component name, which becomes a matrix column.
    The cite is the line that emits (publish, apply, append, send) or consumes (the handler method,
    the `@EventSourcingHandler`, the subscription). An optional ` -> <flow-id>` at the end of the
    fact part links to the flow where it happens; the flow id must exist under `Flows`.
  - `outside: <system> `<handle>``: the event comes from, or goes to, a system outside the
    repository. The handle is the topic, exchange or stream name; for an in-process framework event
    it is the framework class that publishes it (`outside: Spring Boot `SpringApplication``). The cite is the line of the config
    or code that names the handle. `<system>` becomes a matrix column.
  - A catch-all consumer (a binding such as `event.document.*` whose `default` branch only logs and
    acknowledges) is a `consumes` line for each key that it receives and does not handle. Its fact
    starts with `ignores:` after the component (`- consumes: `DocumentEventConsumer` ignores: logs,
    counts and acks`), and its cite is the `default` line. On the page the mark is `(C)`, not `C`.
  - `none found`, with no cite: the map found no emitter or no consumer. Only one `none found` line
    per key, and not next to another line of the same key.
- A component name should be the name of a part in `Architecture` (its label), so the reader finds
  it there. The check does not enforce this.
- The cite rules of every fact line apply.

The check (`scripts/onboard.py check`) adds the prefix `event`:

| Line | When |
|---|---|
| `event <name>: twice` | Two entries have the same name. |
| `event <name>: missing <key>` | No `type`, `stream`, `emits` or `consumes` line. |
| `event <name>: <key> twice` | A second `type`, `payload` or `stream` line. |
| `event <name> #<n>: unknown key <key>` | A line whose key is not one of the five, or a line with no key. |
| `event <name> #<n>: no component in backticks` | An `emits` or `consumes` line that is not `none found` and has no text in backticks. |
| `event <name> #<n>: flow <id> not in Flows` | A ` -> <flow-id>` that names no flow. |
| `event <name>: none found beside a line` | A `none found` line of a key that has another line. |
| `events #<n>: not a dismissal` | A line before the first entry that is not `not an event: ...`. |

The cite lines of the entries use the scope `Events/<name>`, as the flows use `Flows/<id>`. With
`--inventory`, each `event` hit adds `inventory <path>:<line>: not in Events` when no `type` line, no
`payload` line and no dismissal cites its line. `Events` with `none found` has no entries and is checked for nothing
else, but the inventory rule still applies (an event hit then needs a dismissal, so `none found`
cannot hide a found declaration: the section holds the dismissals and no entry).

`Where to look` gains the key `add-event`, required when `Events` has at least one entry: the path
where new event types are declared.

### 16.4 The inventory

`onboard.py inventory` adds one kind, `event`, after the five entry kinds. An `event` hit is a
declaration, not an entry point, so it is not one of `ENTRY_KINDS` and is not a kind of an
`Entry points` line. The patterns:

- Java and Kotlin: a class, record, interface, object or data class whose name ends in `Event`
  (`class OrderPlacedEvent`, `record OrderPlaced...Event(`), a class that extends `ApplicationEvent`,
  and the annotations `@DomainEvent` and `@Event` on a type.
- Go: `type <Name>Event struct`.

An annotation hit (`@DomainEvent`, `@Event`) is reported at the type declaration it annotates,
found by a look-ahead like `_declares_type`, with the text of that declaration line. Thus one event
gives one hit, and its line is the line that a `type` or `payload` line cites. A declaration that both
an annotation and the name suffix match is one hit.

Two patterns join the `listener` entry kind, because they are entry points of a flow: the Axon
annotations `@EventHandler`, `@SagaEventHandler` and `@CommandHandler` (JVM), and
`SubscribeTo\w*\(` (Go, the EventStoreDB client). `@EventSourcingHandler` is not an entry point
(it rebuilds an aggregate); it is not in the inventory, and rule 6 lists it as a consumer.

The last line of the inventory output becomes `inventory: <n> entry points, <m> event types`.
`inventory.txt` keeps the same tab format; the kind column holds `event` for the new hits.

### 16.5 The page

A new section `#events`, "Which events move through <service>?", after `#state` and before the
reference sections. It is omitted when `Events` has no entry. Its parts, in order:

- A lead paragraph: how many events, where they are stored or sent, and the one or two that carry
  the main flows.
- The matrix: a table (`.table-wrap > table.matrix`). One row per event, in map order; the first
  cell is the event name in `<code>`. One column per component and per outside system, in the order
  of their first appearance in the map. A cell holds `E` (emits), `C` (consumes) or both, and is
  empty otherwise. Each `E` or `C` is a link to the flow section of its line (`#flow-<flow-id>`)
  when the line has a flow id, and plain text when it has none. Each mark has a `title` that says the
  sentence in full ("`OrderAggregate` emits `OrderPlaced` when ..."). An `ignores:` consume shows
  `(C)`. A row with a `none found`
  key shows `none found` in an extra last column, "gaps", that names the key. A sentence above the
  table explains `E`, `C` and the links.
- The detail: one `details.walk` per event, with the id `event-<slug>`, after the table. Its
  summary is the event name. It holds the payload type, the stream, and the emit and consume lines
  in words with their cites. The event name in the first cell of the row links to it.
- A `div.cites` after the table carries the cites of the `type` lines, so the section holds a
  `<cite>` even when every detail is closed.

`table.matrix` gets a style in `templates/page.html`: centered mark cells, a sticky first column,
and the column headings written so a narrow screen scrolls the table, not the page. The `#entry`
table lists the new `listener` hits like any other. The nav gets a link to `#events` when the page
has it. The glossary defines each event-sourcing term that the page uses (aggregate, event store,
stream, projection, saga).

### 16.6 The course

`course/map-task.md` names the sections of the rung file by title, so the map of a course source
gets `Events` too. Its override line about `none found` (`Architecture`, `Flows` and `State`) adds
`Events`. `course.py` reads only the flows, so it does not change.

### 16.7 Files and tests of this follow-up

- `scripts/onboard.py`: `TITLES` gains `Events` after `State` (thirteen titles); a constant of the
  four event keys; `parse_map` reads `### <event-name>` entries under `Events` as it reads the flows
  under `Flows`; new functions for the `event` lines and the `events` dismissal lines, called from
  `check_map` after `_entry_lines`; `_cite_scopes` adds `Events/<name>`; `_unlisted_lines` covers
  `event` hits; `PATTERNS` and the inventory summary as in 16.4, with `ENTRY_KINDS` excluding
  `event`; `WHERE_KEYS` gains `add-event` with its condition.
- `tests/test_onboard.py`: one case for each new check line and for the `none found` and `outside:`
  forms; inventory cases for each new pattern and for the new summary line; the fixture
  `tests/fixtures/onboard/map.md` and its `tree` gain an `Events` section with two events (one with
  an `outside:` consumer), and the source files they cite.
- `rungs/onboard.md`: rule 6 of "Explore the service" and the renumbering; the inventory table gains
  the `event` row and the new `listener` patterns; the skeleton and the format rules of "The map";
  the prefix table gains `event`, `events` and the new `inventory` form; "Plan the sections" adds
  `#events`. `tests/test_rung_drift.py` follows: nine rules, thirteen titles, the new prefixes, the
  `#events` id, the event keys and `add-event`.
- `templates/page.html`: the `table.matrix` style. `tests/test_page_template.py` and the onboard
  fixture page (`tests/onboard_page.py`, `tests/fixtures/onboard-page/section.html`) gain one small
  matrix so the snapshot and the font guard see it.
- `course/map-task.md`: the `none found` override line.
- Proof: the diadoc output of 2026-10-17 is extended by hand: an `Events` section with every
  routing key that `EventClassifier` returns (about nineteen, among them `event.document.signature`,
  `event.document.rejection`, `event.document.revocation-request`, `event.document.nonformalized`,
  `event.template.transformation`, `event.template.refusal`) plus `event.unknown`; the in-process
  `DiadocAuthorizedEvent`, `DiadocDeauthorizedEvent` and `ApplicationReadyEvent`; `BoxEvent` as the
  `payload` of the routing-key entries; `StaleEvent` named or dismissed by what the code does with
  it; the `add-event` line; and the `#events` section of the page. `onboard.py check` prints `onboard: ok` and `verify.sh` prints all
  `ok`. The output stays untracked.

### 16.8 Calls made by the author (check these)

1. One repository only. Reason: the rung explores one service directory; the user did not say
   whether the system spans services, and `outside:` lines keep the edge visible.
2. A matrix of events × components with `E`/`C` marks that link to the flows, plus one collapsed
   detail per event. Reason: the user asked for "matrix or something that allows to follow such
   systems easily"; a row follows one event, a column shows what one component touches, and the
   links turn the matrix into a way to follow, not only to look up. The details keep the payload and
   the cites out of the reading flow (memory: evidence on demand, not in the reading flow).
3. `Events` is always present, `none found` when the service has no events, rather than a section
   added only for event-based services. Reason: the check stays a fixed skeleton, and the inventory
   rule makes `none found` impossible when a declaration is found.
4. Event names are verbatim from the code, never normalized. Reason: the point is to search for the
   name you see in a log or a topic.
5. The inventory pattern for event types is a name suffix (`...Event`) plus a few annotations and
   `ApplicationEvent`. Reason: cheap and Java/Kotlin/Go only (memory: no other ecosystems unless
   asked); routing keys and event-type strings are not found by pattern, so rule 6 tells the explorer
   to read for them. False hits are dismissed with a reason.
6. `@EventHandler`, `@SagaEventHandler`, `@CommandHandler` and Go `SubscribeTo...(` become
   `listener` entry points; `@EventSourcingHandler` does not. Reason: the first group starts a flow;
   an event-sourcing handler only rebuilds an aggregate.
7. No choreography diagram. Reason: with tens of events it exceeds the 25-node limit, and the matrix
   with links carries the same information without layout work.
8. A map written before this change fails the check (`section: missing Events`), as in 15. It is
   rewritten, not grandfathered.

After the builder check (2026-10-18), five more:

9. A framework event (declared outside the root) is an entry. Its `type` cites the first line under
   the root that names it, and its emitter is `outside:` with the framework class as the handle.
   Reason: diadoc's readiness flow starts at `ApplicationReadyEvent`; leaving it out would break the
   anti-goal on flow labels.
10. The diadoc proof covers every event, not the examples of the first draft. Reason: goal 1 says
    each event; a proof on a subset proves nothing about the floor.
11. A new optional key `payload` holds the payload class when the event name is a routing key or a
    type string. The inventory hit of the payload class is covered by that cite. Reason: dismissing
    `BoxEvent` as "not an event" would put a false sentence on the page.
12. A catch-all consumer is a `consumes ... ignores:` line for each key that it drops, shown as `(C)`.
    Reason: it is true that the event reaches that consumer, and `(C)` keeps the reader from
    thinking that the event is handled; `none found` would be false.
13. An annotation hit is reported at the declaration line it annotates, and one declaration is one
    hit. Reason: the hit and the `type` cite must be the same line, or a real event could only pass
    with a false dismissal.
