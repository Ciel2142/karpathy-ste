# explain onboard: a Markdown page for Confluence, with PlantUML diagrams rendered to PNG

Date: 2026-11-02. Status: draft, builder check done 2026-11-02 (its four questions are settled in
section 14, items 11 to 14). Coverage: not opted in.

## 1. Problem

The onboard rung (`/explain <service-dir> --as onboard`, spec of 2026-10-16) explores one service into a
checked map and then writes a self-contained HTML page with Mermaid flows rendered to inline SVG. The
user wants the page where an onboarding page lives: in the team wiki. Their Confluence takes a Markdown
file, pasted into the editor or pushed by an importer, and it takes images as attachments. It renders
no Mermaid and no PlantUML by itself. The user asked for three things:

- the output is a Markdown file for Confluence, in place of the HTML page;
- the flows are UML, not BPMN-like flowcharts: "use uml instead of bpmn or the like";
- the diagrams come with PNG files, generated and placed by a script, with a mark in the Markdown
  where each PNG goes, since a Markdown file cannot carry the image bytes.

In the conversation the user settled two more points: the page carries no source citations ("we can drop
source for md"), and the output is for Confluence in general, not for one instance with one plugin.
PlantUML is installed on this machine (Homebrew `plantuml` 1.2026.9 with Graphviz 16.1.0 and OpenJDK 27).

## 2. Goals, non-goals, anti-goals

Goals:

- `/explain <service-dir> --as onboard` writes `page.md`, a Markdown page that a Confluence page takes
  when it is pasted or imported, plus `diagrams/<id>.puml` and `diagrams/<id>.png` for each diagram. The
  page marks the place of each PNG with a standard Markdown image line.
- The map writes each diagram as PlantUML from the start: an activity diagram for each flow, a component
  diagram for the architecture, a state diagram for the state. `onboard.py check` reads PlantUML as it
  reads Mermaid today, with one cited fact for each node. The map stays the source of truth, and the only
  evidence of the run, since the page holds no cites.
- A script copies each fence of the map to its `.puml` file, renders every `.puml` to a PNG through the
  installed PlantUML, and a check proves that the page places every diagram, that every image line names
  a file, and that every picture on the page is the map's own drawing.
- The prose rules of every rung stay: the STE profile, the short answer first, one idea-carrying diagram
  first, code in code blocks and never inline, and a `Not covered` list.

Non-goals:

- No change to the course rung, its lessons or the hub. A course map keeps Mermaid, because the lessons
  render Mermaid into HTML pages. Section 11 carves this out.
- No change to the page, sheet, lesson, video, brainrot or sdr rungs. The HTML onboarding page is removed,
  not kept beside the Markdown.
- No publishing: no Confluence REST client, no `mark` configuration, no page tree. The output is files.
- No PlantUML macro, no Mermaid macro, no Expand macro and no other Confluence-only markup in the page.
- No source citations on the page. No "Sources" blocks, no footnotes.

Anti-goals (a failure even if it runs):

- A diagram on the page that is not the map's fence verbatim: a hand-drawn or hand-edited `.puml`.
- A flow of the map with no section or no picture on the page. Every flow of the map is on the page.
- A PNG on the page that shows PlantUML's own error picture (a syntax error still writes a PNG).
- A command inline in the prose, or a Markdown construct that Confluence does not take: HTML, footnotes,
  a definition list, an intra-page link.
- A node in a diagram without a cited fact line in the map.

## 3. Constraints

- The onboard rung needs `plantuml` on `PATH` (Homebrew `plantuml`, which installs a JDK and Graphviz).
  Chrome is no longer needed for this rung. `plantuml -version` is the test.
- PlantUML facts measured on 2026-11-02 with 1.2026.9: `-tpng -o <dir>` renders many files in one
  process (three diagrams in 0.8 s); a syntax error prints `Error line <n> in file: <path>` and
  `Some diagram description contains errors` on stderr, exits with code 200, and still writes a PNG with
  the error text; `-checkonly` exits 0 or 200 with the same message; Russian labels render; the
  `#color:action;` prefix is deprecated and paints a warning banner into the PNG; a `skinparam` from the
  command line (`-Sdpi=144`) applies to every diagram without a line in the source; `-charset UTF-8` is
  needed for Cyrillic; `-metadata <png>` recovers the source from a PNG.
- Confluence takes pasted or imported Markdown as headings, paragraphs, bullet lists, pipe tables, fenced
  code blocks and images. A relative image path becomes an attachment through an importer; by hand, the
  reader uploads the PNG at the image line. It does not render HTML, footnotes or definition lists, and
  pasted tables need a blank line above and below them.
- `ste_lint.py` reads Markdown in its default mode: fenced code, headings and table rows yield no
  sentences; an image line is prose whose link destination is opaque, so the alt text is linted as one
  sentence (measured 2026-11-02).
- PlantUML activity actions have no ids. A node fact of an activity diagram is keyed by the node's
  visible label, so labels are unique inside one diagram and hold no backtick.

## 4. Approaches

- **A. The map keeps Mermaid; the page gets PlantUML.** The author translates each Mermaid flow into an
  activity diagram when writing the page. Trade-off: every flow is drawn twice, and no check can prove
  that the activity diagram has every branch of the map flow. That is the flattening the onboard rung was
  built to stop, and with no cites on the page, the evidence would sit on a drawing the reader never sees.
- **B. The map speaks PlantUML (chosen).** The onboarding rules write PlantUML fences; the check parses
  them; the page copies them verbatim; one script renders the PNGs. Trade-off: a small PlantUML parser in
  the check and a few syntax rules for the activity form.
- **C. Convert Mermaid to PlantUML automatically (dropped).** A free flowchart does not map onto the
  structured activity syntax reliably; the `goto`/`label` escape is experimental and draws badly.

The user chose B ("keep it as you said").

## 5. Command

Unchanged: `/explain <service-dir> --as onboard`, forced only, one directory, English or Russian, no
review, the rung line `Rung: onboard (forced) — <reason> — subject: <path> (directory)`.

New, before the build: run `plantuml -version`. If it fails, print the rung line, say that the onboard
rung needs PlantUML (`brew install plantuml`), and stop. Offer `page`.

## 6. Output directory

`~/karpathy/out/YYYY-MM-DD-HHMMSS-onboard-<slug>/` (convention 5 of `SKILL.md`).

| Path | Holds |
|---|---|
| `map.md` | The onboarding map. The source of truth of the page and its only evidence. |
| `inventory.txt` | The entry points and event types that `onboard.py inventory` found. |
| `diagrams/<id>.puml` | One PlantUML diagram: the fence of the map verbatim, wrapped in `@startuml` and `@enduml`, written by `onboard.py diagrams`. |
| `diagrams/<id>.png` | Its render, written by `puml.py render`. |
| `page.md` | The onboarding page, Markdown for Confluence. |

`<id>` is `architecture`, `flow-<flow-id>` or `state`. No `index.html`, no snapshots, no `review/`.

## 7. The map in PlantUML

### 7.1 Which notation

An onboard run draws every diagram of the map in PlantUML, in a fence with the info string `plantuml`.
A course map draws every diagram in Mermaid, as today (section 11). `onboard.py check` reads both
notations and takes `--notation plantuml|mermaid`; with the flag, a fence of the other notation fails as
`diagram <where>: not plantuml` or `diagram <where>: not mermaid`. Without the flag both pass. The
onboard rung passes `--notation plantuml`; the course passes `--notation mermaid`.

The three places keep their kinds: `Architecture` holds one component diagram, each flow holds one
activity diagram, `State` holds one state diagram or `none found`. The check detects the kind of a
PlantUML fence from its text: activity when its first statement is `start`; state when a line starts with
`[*]` or `state `; component when it declares a part (7.3) or draws an edge between two ids; else
`diagram <where>: not a PlantUML kind`. A wrong kind fails as `diagram <where>: not activity`,
`not component` or `not state`.

### 7.2 Flows: the activity form

Rule 4 of "Explore the service" and "The map" get these rules in place of `flowchart TD`:

- The fence starts with `start` and ends with `stop` or `end`.
- One action is one line: `:<label>;`. The label is the text between `:` and `;`. It holds no backtick.
  An action over several lines fails.
- A label names one node. The same label in two places of one diagram is the same node, drawn twice,
  with one fact line. That is how two branches rejoin on one action, for example a shared error reply:
  structured activity syntax has no other merge.
- A branch is `if (<condition>) then (<outcome>)`, optional `elseif (<condition>) then (<outcome>)`
  lines, optional `else (<outcome>)`, and `endif`. A loop is `while (<condition>) is (<outcome>)` to
  `endwhile (<outcome>)`, or `repeat` to `repeat while (<condition>) is (<outcome>)`. A choice of many
  is `switch (<condition>)`, `case (<outcome>)` lines and `endswitch`. The condition is a node. Each
  outcome is an edge label, not a node. Every condition of the code path is one of these, as today: each
  `if`, `when`, `switch`, strategy choice, `catch`, retry loop, timeout and feature flag.
- An exit that is an error is an action followed by `stop`, `kill` or `detach`.
- A hop into a flow that another flow draws is the action `:see <flow-id>;` followed by `detach`. The
  flow id exists under `Flows`.
- `fork`, `fork again` and `end fork` draw parallel work. `partition "<name>" {` and `}` group actions.
  `-> <label>;` labels an edge. `note` lines and `' ` comments are allowed. None of these is a node.
- Not allowed, and the check reports them: `skinparam`, `!pragma`, `!include`, `<style>`, a colour prefix
  such as `#pink:`, `split`, `backward:`. The style lives in the renderer (section 8).
- A diagram has at most 25 nodes: the distinct labels of its actions and conditions.
- The parser is tolerant, as the Mermaid parser is: a line that is none of the forms of 7.2 to 7.4 and
  none of the forbidden lines is ignored. Examples are `title`, `legend`, `left to right direction`,
  `hide empty description` and a `note` block. Every arrow form counts as an edge (7.3, 7.4), so no part
  on an edge escapes the fact floor.

The node fact of an activity node is keyed by its label in backticks, verbatim:

```
- `pending states at capacity?`: the capacity guard refuses a new login when the map of states is full | src/.../OidcCallbackController.java:118 | if (pending.size() >= MAX_PENDING)
- `see readiness`: the authorized event wakes the readiness coordinator | src/.../OidcCallbackController.java:214 | publisher.publishEvent(new DiadocAuthorizedEvent())
```

The cite of a condition is its condition line; the cite of an action is the call line, as today.

### 7.3 Architecture: the component form

Rule 3 gets these rules in place of `flowchart LR`:

- Each part is declared once, with an alias: `component "<name>" as <id>`, `queue "<name>" as <id>`,
  `database "<name>" as <id>`, `cloud "<name>" as <id>`, `node "<name>" as <id>`,
  `rectangle "<name>" as <id>`, `interface "<name>" as <id>`, `actor "<name>" as <id>`, or
  `[<name>] as <id>`. A component is a part inside the service, a queue or a database is a store, a
  cloud or a node is another system. An id matches `[a-z][a-z0-9_]*` (no hyphen: PlantUML reads a
  hyphen as an arrow).
- An edge is any PlantUML arrow between two parts, with an optional `: <label>`: `-->`, `->`, `..>`, a
  direction such as `-left->`, or a styled arrow such as `-[hidden]->`. `..>` draws a read or a lookup.
  An endpoint is an alias or a bracket form `[<name>]`; a bracket form on an edge without a declaration
  is not declared.
- `package "<name>" {` and `}` group parts and are not nodes.
- A node of the check is each declared alias and each id on an edge. An id on an edge without a
  declaration fails as `node architecture/<id>: not declared`.

The node fact is keyed by the id, as today: `- <id>: <fact> | <path>:<line> | <snippet>`.

### 7.4 State: the state form

Rule 5 gets these rules in place of `stateDiagram-v2`:

- `[*] --> <STATE>` enters, `<STATE> --> <STATE> : <event>` moves, `<STATE> --> [*]` ends. A state can
  have a label: `state "<label>" as <STATE>`. A composite `state <STATE> {` to `}` holds inner states.
- A state is each id on either side of an arrow of any form (`-->`, `->`, `-left->`) and each declared
  state, never `[*]`. Ids match `[A-Za-z_][A-Za-z0-9_]*`.

The node fact is keyed by the state id, as today.

### 7.5 The check

`onboard.py check <map.md> --root <root> [--inventory <file>] [--notation plantuml|mermaid]`. Every rule
of today stays. New failure lines:

| Prefix | Meaning |
|---|---|
| `diagram <where>: not plantuml` / `not mermaid` | With `--notation`: a fence of the other info string. |
| `diagram <where>: not a PlantUML kind` / `not activity` / `not component` / `not state` | A `plantuml` fence of no kind or of the wrong kind for its place. |
| `diagram <where>: action over lines <n>-<m>` | A `:` line without `;` on the same line. |
| `diagram <where>: style line <n>` | A `skinparam`, `!pragma`, `!include`, `<style>`, colour prefix, `split` or `backward:` line. |
| `node <where>/<label>: flow <id> not in Flows` | A `see <flow-id>` action whose id is not a flow. |
| `node architecture/<id>: not declared` | An id on an edge of the component diagram without a declaration. |
| `node <where>/<id>: bad id` | A component or state id outside its pattern. |

`node <where>/<label>: no fact line`, `fact <where>/<label>: not a node` and `fact <where>/<label>:
two lines` keep their form, with the label where the id was. The `_key` of a fact line that starts with a
backtick is the text up to the closing backtick.

`diagram <where>: <n> nodes, more than 25` applies to the activity form too: `<n>` counts the distinct
labels of its actions and conditions.

## 8. `scripts/puml.py`

One new module. It holds the PlantUML parser that `onboard.py check` uses (7.1 to 7.4: the kind of a
fence, its nodes, its faults), and one command:

```
puml.py render <diagrams-dir>
```

- Finds `plantuml` on `PATH`. Without it: `plantuml: FAIL plantuml not found`, exit 2.
- Runs one process for every `.puml` of the directory:
  `plantuml -tpng -charset UTF-8 -o <abs dir> -Sdpi=144 -SbackgroundColor=white -Sshadowing=false
  -SdefaultFontSize=14 <files>`. The style is fixed in the script, as `mermaid_svg.py` fixes its config:
  a fence writes no style. White, because a Confluence page is white.
- Reads stderr for `Error line <n> in file: <path>` and prints `plantuml: FAIL <id> line <n>` for each,
  where `<n>` is the line inside the fence (PlantUML counts the `@startuml` wrapper line, measured
  2026-11-02; the script subtracts it); removes the PNG of each failed id, so that no error picture reaches the page. A non-zero exit with no
  such line is `plantuml: FAIL exit <code>`. A `.puml` with no PNG after the run is
  `plantuml: FAIL <id> no png`.
- Last line on success: `plantuml: ok <n> diagrams`. Exit 0, or 1 when a line failed.
- An empty directory is `plantuml: ok 0 diagrams`.

The test of `render` skips when `plantuml` is not on `PATH`, with the message `plantuml missing`, as the
Mermaid tests skip without their bundle.

## 9. `onboard.py diagrams` and `onboard.py page`

Two new commands of `onboard.py`, with their code in a new module `onboard_page.py` that `onboard.py`
imports, as `bpmn.py` imports `bpmn_check.py`.

```
onboard.py diagrams <map.md> --out <diagrams-dir>
```

Reads the map. Writes `architecture.puml`, `flow-<flow-id>.puml` and `state.puml`: the lines of the fence
verbatim between `@startuml` and `@enduml`. A place that is `none found` writes no file. Prints
`diagrams: stale <file>` for each `.puml` of the directory that no fence produced (it deletes nothing),
then `diagrams: ok <n> files`. Exit 0; 2 when the map cannot be read; 1 when the map has a `mermaid`
fence (`diagrams: <where>: not plantuml`).

```
onboard.py page <page.md> --map <map.md>
```

Checks the page against the map and the `diagrams/` directory beside the page. One failure per line,
then `page: ok` or `page: <n> failures`. Exit 0, 1, or 2 when the page or the map cannot be read. The
checks are content checks that hold in English and in Russian, since every checked text comes from the
map:

| Prefix | Meaning |
|---|---|
| `page: no title` / `page: second title` | The first non-blank line is not `# `, or a second `# ` line exists. |
| `page: no short answer` | The first paragraph after the title does not start with bold text. |
| `diagram <id>: no image line` / `diagram <id>: image line twice` | A `.puml` of the map with no `![…](diagrams/<id>.png)` line, or two. |
| `image <path>: no file` / `image <path>: not under diagrams/` / `image <path>: not in the map` | An image line whose file is missing, outside `diagrams/`, or whose `<id>` is not `architecture`, `state` or a `flow-<flow-id>` of the map. The last closes the goal that every picture on the page is the map's own drawing. |
| `png <id>: no image line` | A PNG in `diagrams/` that no image line names. |
| `diagram <id>: differs from the map` / `diagram <id>: no puml` / `puml <id>: not in the map` | The `.puml` body is not the fence verbatim; a fence without its file; a file without its fence. |
| `flow <id>: no section` / `flow <id>: image outside its section` / `flows: out of map order` | No `## <question>` heading verbatim; the flow's image line is not under its heading; the flow headings are not in map order. |
| `entry <name>: not on the page` | A traced or not-traced entry point of the map whose name is not on the page. |
| `event <name>: not on the page` | An event of the map whose name is not on the page. |
| `not covered #<n>: not on the page` | A `Not covered` line of the map whose text is not on the page. |
| `command <key>: not in a code block` | The `build`, `test` or `run` command of `Shape` is not on a line inside a fence, or appears outside one. |
| `paragraph <line>: two lines` | Two text lines in a row that are not a list, a table, a fence or a heading. |
| `html <line>: tag outside code` | An HTML tag outside backticks and fences. |
| `cite <line>: map line on the page` | A line of the shape `… | <path>:<n> | …`. |

The page check does not read the headings of the fixed sections: their words are the author's, in the
language of the page. It reads the flow headings, which are the questions of the map verbatim.

## 10. The page

### 10.1 Markdown for Confluence

- ATX headings only. One `# ` line, the title. Every other heading is `## `.
- A paragraph is one line. No hard wraps.
- Bullet lists with `- `. Tables are pipe tables with a header row and a `|---|` row, with one blank
  line above and below.
- Code is fenced with an info string (`sh`, `yaml`, `text`). A command is never inline. A code name in
  the prose is in backticks.
- A diagram is one image line alone on its line, with a blank line above and below:
  `![<caption>](diagrams/<id>.png)`. The caption is one STE sentence that says what the picture shows.
  The lint reads it.
- Bold only for the label of the short answer. No HTML, no footnotes, no definition list, no link inside
  the page: name a section by its heading in words ("see the section ..."). A URL is allowed in the last
  section only.

### 10.2 The section plan

This plan replaces section 4 of `rungs/onboard.md`. The section count follows the flows: never merge
flows.

1. `# <question>`: what the service does and why it exists.
2. The short answer: one paragraph that starts with `**Short answer.**`, two to four sentences, at most
   70 words: the purpose, the runtime kind and the main flows by name, from `Shape`.
3. `## What is <service> made of?`: a lead paragraph, the architecture image, then one paragraph for
   each other system and each store of the diagram.
4. `## How do I build, test and run it?`: a table with one row for each `language` and `framework` line
   (name, version). Then for `build`, `test` and `run`, in this order, one sentence and one fenced code
   block with the command alone. A `none found` line is one sentence and no block.
5. `## Where does a message enter?`: a table with one row for each traced or not-traced entry point:
   kind, name in backticks, and the question of its flow, or "not traced" with the reason.
6. One section for each flow, in map order. Its heading is the question of the flow, verbatim. It holds
   a lead paragraph (what comes in, what leaves), the flow image, one paragraph for each condition that
   names its outcomes and says why the branch exists, one paragraph for each action that calls another
   system or writes a store, and one sentence for each `see <flow-id>` that names the section of that
   flow by its heading.
7. `## Which states does a message go through?`: the state image and one paragraph for each state.
   Omitted when `State` is `none found`.
8. `## Which events move through <service>?`: a lead paragraph, one sentence that explains the marks, the
   matrix as a pipe table (one row for each event, one column for each component and outside system,
   cells `E`, `C`, `E C` or `(C)`, a last column `gaps` when a `none found` line exists), then one bullet
   for each event: its payload, its stream, who emits it in which flow and who consumes it in which flow.
   Omitted when `Events` has no entry.
9. `## Which formats and transforms does it use?`, `## Which config routes a message?`,
   `## What happens on an error?` (a list; each item names the flow section where it happens),
   `## Which other systems does it talk to?` (a table of system and handles). Each is omitted when its
   map section is `none found`.
10. `## How is the code written?`: one paragraph for each `Conventions` line; a `none found` topic is one
    sentence. Omitted when every line is `none found`.
11. `## Where do I look to change something?`: a table of task and path in backticks. Omitted when
    `Where to look` is `none found`.
12. `## Terms`: a table of term and meaning, when the page uses a term that a newcomer does not know.
13. `## Not covered`: one bullet for each `Not covered` line of the map and each not-traced entry point
    with its reason; `none` when there is none.
14. `## About this page`: a table with Subject (the service path), Root, Commit, Dirty, Date and the
    command (`/explain <path> --as onboard`).

The English wording above is the default. A Russian page translates the fixed headings and keeps the
structure (convention 7 of `SKILL.md`).

### 10.3 Write and verify

This replaces section 5 of `rungs/onboard.md`. In the output directory, in this order:

1. Write `map.md` by "Explore the service" and "The map". Run
   `onboard.py check map.md --root <root> --inventory inventory.txt --notation plantuml` until
   `onboard: ok`.
2. Run `onboard.py diagrams map.md --out diagrams`. Then `puml.py render diagrams` until
   `plantuml: ok <n> diagrams`. A `plantuml: FAIL` line is fixed in the map fence, never in the `.puml`
   file; then run both commands again.
3. Read each `diagrams/<id>.png` with the Read tool. Look for a cut label, a label over a line, a
   condition without an outcome label, an empty branch, and a false picture of the code. Fix the map
   fence, rerun step 1 and 2.
4. Write `page.md` by 10.1 and 10.2.
5. Run `onboard.py page page.md --map map.md` until `page: ok`.
6. Run `python3 <skill-dir>/../ste/scripts/ste_lint.py page.md` until `0 errors`.
7. Read `page.md`. Cover the page below the short answer: does the answer alone answer the title? Cover
   the prose of the first section: does the architecture picture alone support the answer? Compare the
   entry table with `inventory.txt`: each traced or not-traced entry line has a row.
8. Handoff: print the path of `page.md`. When you run for the user directly, run `open <output-dir>` so
   that the user can take the page and the PNGs. Never run `open` inside a subagent.

## 11. The course keeps Mermaid

- `course/map-task.md` gets one override: "Draw each diagram as Mermaid, in a `mermaid` fence:
  `flowchart LR`, `flowchart TD` and `stateDiagram-v2` as "Explore the service" says for a course map. The
  PlantUML rules of an onboard run do not apply: the lessons render Mermaid." Its check command gets
  `--notation mermaid`.
- `rungs/course.md` section 3: the orchestrator's check command gets `--notation mermaid`.
- "Explore the service" opens with one paragraph: an onboard run draws PlantUML, a course map draws
  Mermaid, and the rules below name both forms. Rules 3, 4 and 5 give the Mermaid form in one clause each,
  as today, and the PlantUML form by sections 7.2 to 7.4.
- `course.py` and `lesson-task.md` do not change: `onboard.flow_nodes` returns the Mermaid node ids of a
  course map as today. For a PlantUML map it returns the labels; nothing reads them.

## 12. `SKILL.md`, `README.md`, removals

- `SKILL.md`: the rung table row becomes "`onboard` (Markdown page from a checked map, directory
  output)"; the rung bullet says that it builds one Markdown page for one service from its map, with
  PlantUML diagrams rendered to PNG; the Rung files bullet names the map, the PlantUML diagrams, the
  Markdown page and its check. The conventions get the onboard exceptions: convention 1, the page is
  `page.md` and passes `ste_lint.py` without `--html`; convention 2, the cites live in the map and the page
  holds none; convention 3, the artifact is the output directory (`page.md` and `diagrams/*.png`);
  convention 4, the checks are `onboard.py check`, `puml.py render`, `onboard.py page` and the lint;
  convention 6, the handoff opens the output directory. The Build procedure step 2 says "For an onboarding
  page, the rung file replaces steps 3 to 6."
- `README.md`: the onboard clause of the `--as` list (a Markdown page for Confluence with PlantUML
  diagrams rendered to PNG, no cites on the page), the requirements row (`plantuml` on `PATH`, from
  Homebrew; no Chrome), the structure lines (`scripts/{onboard,onboard_page,puml,mermaid_svg}.py`).
- Removed, because the onboard rung no longer writes HTML: the `rung=onboard` case and the usage text of
  `verify.sh`; `onboard` in `RUNGS` and `USAGE` of `bpmn.py`; `tests/onboard_page.py`,
  `tests/fixtures/onboard-page/` and the tests that use them in `test_verify.py`, `test_bpmn_check.py` and
  `test_page_template.py`; the `table.matrix` rules of `templates/page.html` and the `#events` matrix tests,
  since only the onboard page used them. Section 6 of `rungs/onboard.md` lists the new output.

## 13. Files and tests

New: `scripts/puml.py`, `scripts/onboard_page.py`, `tests/test_puml.py`, `tests/test_onboard_page.py`,
fixtures `tests/fixtures/onboard/map-puml.md` (a PlantUML map of the same `tree`, passing
`--notation plantuml`), `tests/fixtures/onboard/parser-activity.puml`, `parser-component.puml`,
`parser-state.puml` (one of each kind with every allowed construct), `tests/fixtures/onboard/page.md` (a
page of `map-puml.md` that passes `onboard.py page`).

Changed: `rungs/onboard.md` (sections 1 to 6), `SKILL.md`, `README.md`, `course/map-task.md`,
`rungs/course.md`, `scripts/onboard.py` (the notation flag, the dispatch to `puml.py`, the two commands,
`_key` on a backtick label), `scripts/verify.sh`, `scripts/bpmn.py`, `templates/page.html`,
`tests/test_onboard.py` (the notation flag, the PlantUML places, the fixture map), `tests/test_rung_drift.py`
(the onboard titles, the plan bullets, the output table, the SKILL.md row and conventions),
`tests/test_course_prompts.py` (the `--notation mermaid` command and the override), `tests/test_verify.py`,
`tests/test_bpmn_check.py`, `tests/test_page_template.py`.

Tests that run `plantuml` skip without it, with `plantuml missing`. The parser, `diagrams` and `page` tests
need no PlantUML.

Proof at the end: run `/explain <one real service> --as onboard` on a repository of the user (the diadoc
service of the 2026-10-19 run), read every PNG, run the three checks and the lint, and open `page.md` in
a Markdown viewer. The user pastes it into a Confluence page and attaches the PNGs; that step is theirs.

## 14. Calls made by the author (check these)

1. One Markdown file for the whole service, not a page tree. Reason: it mirrors the HTML page and keeps
   the placing of PNGs by hand to one page; a tree is a later option.
2. The marker of a PNG is the standard image line with the caption as alt text, not a custom token.
   Reason: every importer and every reader understands it, and the lint checks the caption.
3. The `.puml` source stays in `diagrams/` and is not repeated on the page. Reason: a code block of
   PlantUML on a Confluence page without the macro is noise; the file beside the PNG is enough to edit.
4. Flows are activity diagrams, the architecture a component diagram, the state a state diagram.
   Reason: these are the UML forms of a branching path, a set of parts and a lifecycle.
5. The key of an activity node fact is its label in backticks. Reason: PlantUML actions have no ids, and
   an invented id comment would be syntax of our own.
6. White background, 144 dpi, no shadows, 14 px font, set by the renderer. Reason: Confluence pages are
   white; 144 dpi stays crisp when Confluence scales the image; a fence carries no style, as with Mermaid.
7. The renderer removes the PNG of a failed diagram. Reason: PlantUML writes an error picture on a
   syntax error, and a stale one must never reach the page.
8. The page check is content-based and language-neutral; it does not verify the fixed headings. Reason:
   a Russian page has Russian headings, and every checked text (flow questions, entry names, events,
   commands, not-covered lines) comes from the map.
9. The `table.matrix` CSS of the page template and its tests go. Reason: only the onboard HTML page used
   them.
10. The course keeps Mermaid, with `--notation mermaid` on its check. Reason: scope; the lessons render
    Mermaid, and a strict flag stops a course map subagent from drawing PlantUML after reading the
    onboard rules.

After the builder check (2026-11-02), four more:

11. The PlantUML parser is tolerant of unknown lines and strict about edges: every arrow form is an
    edge, every part on an edge must be declared, and a line of no known form is ignored. Reason: the
    fact floor is about nodes; an unrecognised arrow that let a part escape the floor would break the
    anti-goal silently, while a strict whitelist of every PlantUML statement is a parser we do not want
    to own.
12. The same action label twice in one activity diagram is one node with one fact line, not a fault.
    Reason: structured activity syntax has no other way to rejoin two branches on one action, and a
    shared error reply is the common case. The picture shows the box twice; the fact is one line.
13. Every flow of the map is on the page; `Not covered` lists directories and not-traced entry points
    only. Reason: a flow in the map is traced code, and leaving it off the page is the flattening the
    rung exists to stop. The anti-goal of section 2 lost its "unless" clause.
14. `image <path>: not in the map` is a failure of the page check. Reason: without it a hand-made PNG
    with its own image line passed every other line.

## 15. Left to the builder

- The exact regular expressions of the PlantUML parser, within the forms of 7.2 to 7.4.
- The default font name of the renderer (sans; the JDK default is fine).
- The Russian wording of the fixed headings, written in the rung as a table beside the English ones.
- The order of the failure lines of `onboard.py page`.
- How `onboard.py` dispatches a fence to `puml.py` or to the Mermaid parser (by the info string).
