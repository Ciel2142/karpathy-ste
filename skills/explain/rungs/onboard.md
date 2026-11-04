# Rung: onboard
This file holds only what is specific to the onboard rung. `SKILL.md` has the generic rules.

## 1. When an onboarding page

The onboard rung builds an onboarding page: one page that explains one service to a new member of its
team. The page shows the parts of the service, each entry point and the path of each message from its
entry to each exit. Each branch in the code is a branch in a diagram, and each node of a diagram has a
cite.

The onboard rung is a forced rung. Only `--as onboard` selects it. Never choose it from the content.
The command is `/explain <service-dir> --as onboard`.

The build has two parts. First, write a map of the service ("Explore the service" and "The map"). Then
write the page from the map. The map is the source of truth of the page.

The subject is one directory: the directory of the service. If the subject is a file, `this` or a
topic, print the rung line. Say that the onboard rung takes one directory. Stop. Offer `page`.

The onboard rung has no review. If the review is on, print `--review: no effect on onboard` after the
rung line, and continue.

The onboard rung is English or Russian, by the rule of the page rung. Write the page in `en`, or in `ru`
when the user asks for Russian. If the user asks for another language, print the rung line. Say that
the onboard rung is English or Russian. Stop. Offer `page`.

Print this line before you build, as `SKILL.md` says:

```
Rung: onboard (forced) — <reason> — subject: <path> (directory)
```

The `<reason>` names `--as onboard` and tells if the content fits the rung.

After the rung line, run `plantuml -version`. If the command fails, say that the onboard rung needs
PlantUML (`brew install plantuml`). Stop. Offer `page`. The rung line stays as the first line.

Find `<root>` before you explore. Run `git rev-parse --show-toplevel` in the service directory. Its
output is `<root>`. If the command fails, `<root>` is the absolute path of the service directory.
`<root>` is the `--root` of both `onboard.py` commands. Each cite path is relative to `<root>`.

Make the output directory ("Output directory") before you explore. Run the `onboard.py` commands in the
output directory. Make `<service-dir>` an absolute path, because the commands run in the output
directory.

## 2. Explore the service

In this file, `onboard.py <command>` is short for `python3 <skill-dir>/scripts/onboard.py <command>`,
and `puml.py render` is short for `python3 <skill-dir>/scripts/puml.py render`.

An onboard run draws each diagram in PlantUML, in a `plantuml` fence. A course map draws each diagram in
Mermaid, in a `mermaid` fence. The rules below name both forms. The PlantUML form is the main text of
each rule, and a clause tells what a course map draws.

Follow these nine rules, in the order of the work. Write each fact into `map.md`, in the format of
"The map".

1. Shape first. Read the build files, the main config and the entry of the process. Write one
   `Shape` line for each of these keys. A line starts with its key and a colon:
   - `language`: the language and the build tool;
   - `framework`: one framework or runtime library with its version, from the line that pins it. The
     key is optional. Write one line for each library;
   - `runtime`: the runtime kind: web server, consumer, scheduler, batch or library;
   - `artifact`: the deploy artifact: image, jar, binary or chart;
   - `purpose`: the purpose of the service, in one sentence;
   - `build`: the command that builds the service;
   - `test`: the command that runs its tests;
   - `run`: the command that runs the service on a developer machine.

   Write each key once, except `framework`. Put the command of `build`, `test` and `run` in backticks.
   The cite is the line that defines the command. Examples are a Makefile target, a `scripts`
   entry and a plugin line. More examples are a README line, a Dockerfile `ENTRYPOINT` and a CI job
   line. If the source has no such command, write `- <key>: none found` with no cite. Only `build`,
   `test` and `run` take `none found`. `Shape` has no other key. Write a fact of another subject in
   its own section. A port, a queue name or a URL goes in `Routing config`. A retry goes in
   `Error paths`. A pipeline or a registry goes in `Other systems`. Each line holds one fact. Its
   cite shows that fact.
2. Inventory. Run `onboard.py inventory <service-dir> --root <root> --out inventory.txt`. It prints
   one line for each hit: `<path>:<line>`, a tab, the kind, a tab and the text of the line. It writes
   the same lines to `inventory.txt`. The last line of its output is `inventory: <n> entry points, <m> event types`.
   Read each line. The map must account for each entry point of this list. A hit of the kind `event` is
   not an entry point: rule 6 says what to do with it. The script finds patterns, not truth. A hit can be
   false, and the list can miss a real entry point. Add each entry point that
   you find when you read the code. Dismiss a false hit with a reason, as a
   `-> not an entry point: <reason>` line.
3. Architecture. Draw the parts at runtime as one component diagram. A part is a component inside the
   service, a store or another system. The components are the listeners, controllers, services,
   repositories, clients and schedulers, by their real names. A store is a table, a cache, a file
   system or a queue that the service owns. Draw an edge for each call or message between two
   parts. Write one cited fact for each node. Keep to the parts that a message meets. A utility class
   is not a part. These rules apply to the diagram:
   - Declare each part once, with an alias: `component "<name>" as <id>`. The same form holds for
     `queue`, `database`, `cloud`, `node`, `rectangle`, `interface` and `actor`. The bracket form
     `[<name>] as <id>` is also a declaration. Use `component` for a part inside the service. Use
     `queue` or `database` for a store. Use `cloud` or `node` for another system.
   - An id matches `[a-z][a-z0-9_]*`. It has no hyphen, because PlantUML reads a hyphen as an arrow.
   - An edge is an arrow between two parts, with an optional `: <label>`. The arrows are `-->`, `->`
     and `..>`. Use `..>` for a read or a lookup. A direction such as `-left->` and a style such as
     `-[hidden]->` make an arrow too.
   - An end of an edge is an alias. A bracket form `[<name>]` on an edge, with no declaration, is not
     declared.
   - `package "<name>" {` and `}` group parts. A package is not a node.
   - A node is each declared alias and each id on an edge. An id on an edge with no declaration
     fails as `not declared`.
   - A course map draws the parts as one `flowchart LR` in a `mermaid` fence. The Mermaid rules of
     "The map" apply there.
4. Flows. Write one flow for each entry point, or for each group of entry points that take the same
   path. Name a group by the shared path, and list each entry point under it. Trace the flow from
   its entry to each exit. An exit is a reply, a message sent, a row written, or a log line and stop.
   Draw the flow as an activity diagram. These rules apply to each flow:
   - A branch in the code is a branch in the diagram. Each `if`, `when`, `switch`, strategy choice,
     `catch`, retry loop, timeout and feature flag on the path is a decision node. A decision node
     has one edge for each outcome, with the outcome as its label. An exit that is an error is a
     node.
   - Each node has one cited fact under the diagram. The cite of a decision node is its condition
     line. For a `catch`, it is the `catch` line. The cite of a call node is the call line.
   - A node that calls another system names the system and the handle: a queue, an endpoint or a
     table.
   - Put at most 25 nodes in one diagram. A longer flow splits into stages. The parent flow shows
     each stage as one node. Each stage is a flow of its own, with the id `<flow>-<stage>`.
   - A call can enter a method that another flow drew already. Then draw one node that names that
     flow (`see <flow-id>`). Do not draw the nodes again. A wait for an outside event, such as the
     next poll, is a plain action, not a `see`.

   These rules give the PlantUML form of a flow:
   - The fence starts with `start` and ends with `stop` or `end`.
   - One action is one line: `:<label>;`. The label is the text between `:` and `;`. It holds no
     backtick. An action over several lines fails.
   - A label names one node. The same label in two places of one diagram is the same node, drawn
     twice, with one fact line. Use this to join two branches on one action. An example is a shared
     error reply. Structured activity syntax has no other join.
   - A branch is `if (<condition>) then (<outcome>)`, then optional `elseif (<condition>) then
     (<outcome>)` lines, an `else (<outcome>)` line and `endif`. Write the `else` line also when its
     branch holds nothing, so that the picture labels the last outcome. An `if` with no `else` line
     fails as `if without else`, also after an `elseif`.
     A loop is `while (<condition>) is (<outcome>)` to `endwhile (<outcome>)`. A loop can also be `repeat` to
     `repeat while (<condition>) is (<outcome>)`. A choice of many is `switch (<condition>)`,
     `case (<outcome>)` lines and `endswitch`. The condition is a node. Each outcome is a label of an
     edge, not a node.
   - An exit that is an error is an action followed by `stop`, `kill` or `detach`.
   - A hop into a flow that another flow draws is the action `:see <flow-id>;` followed by `detach`.
     The flow id exists under `Flows`.
   - `fork`, `fork again` and `end fork` draw parallel work. Draw the entry points of one flow as the
     branches of one `fork`, before the shared path. `partition "<name>" {` and `}` group
     actions. `-> <label>;` labels an edge. None of these is a node. You can write a `note` or a `'`
     comment.
   - Never write `skinparam`, `!pragma`, `!include`, `<style>`, a colour prefix such as `#pink:`,
     `split` or `backward:`. The check reports them. The renderer sets the style. The fence holds the
     body of the diagram only. Never write `@startuml` or `@enduml` in it, because the check reports
     both lines too. `onboard.py diagrams` adds them when it writes the `.puml` file.
   - The nodes of a diagram are the distinct labels of its actions and conditions.
   - The fact line of an activity node starts with its label in backticks, verbatim. The cite of a
     condition is its condition line. The cite of an action is the call line. For example:

     ```
     - `total over limit?`: the total is checked against the limit | src/main/java/shop/OrderController.java:16 | if (order.total() > LIMIT) {
     - `see order`: the row is saved as in the order flow | src/main/java/shop/OrderListener.java:19 | repository.save(order);
     ```

   - A course map draws each flow as one `flowchart TD` in a `mermaid` fence. The Mermaid rules of
     "The map" apply there.
5. State. Find the entities that a message changes, and each status field with its transitions. Draw
   them as one state diagram. Write one cited fact for each state, from the line that sets it. If
   the service keeps no state, write `none found`. These rules give the PlantUML form:
   - `[*] --> <STATE>` enters, `<STATE> --> <STATE> : <event>` moves and `<STATE> --> [*]` ends. A
     state can have a label: `state "<label>" as <STATE>`. A composite `state <STATE> {` to `}`
     holds inner states.
   - A state is each id on either side of an arrow, in any form (`-->`, `->` or `-left->`), and
     each declared state. `[*]` is never a state. An id matches `[A-Za-z_][A-Za-z0-9_]*`.
   - A course map draws the states as one `stateDiagram-v2` in a `mermaid` fence. The Mermaid
     rules of "The map" apply there.
6. Events. Find each event of the service. An event is a type or a name. One part publishes it
   or appends it to an event store. It can also apply it, or send it to a topic or an exchange. Another
   part handles it. Look for these:
   - event classes and records;
   - `apply(`, `AggregateLifecycle.apply`, event-store appends, `publishEvent` and
     `ApplicationEventPublisher`;
   - Kafka and RabbitMQ sends with an event payload;
   - the routing keys and the event-type strings;
   - the handlers `@EventHandler`, `@EventSourcingHandler`, `@SagaEventHandler` and `@EventListener`;
   - projection handlers and stream subscriptions.

   Write one entry for each event under `Events`, in the format of "The map". A service with no events
   writes `none found`. The inventory lists event declarations as `event` hits. Each must be the cite of a
   `type` line, of a `payload` line or of a `not an event` line. A flow node that emits or consumes an
   event names the event, verbatim, in its fact.
7. Formats and transforms, routing config, error paths and other systems. Write them as fact lines,
   each in its section of the map:
   - `Formats and transforms`: the format of each message, and each change to its format or its
     content. Examples are XML, JSON, a message class, a mapper and an XSLT file.
   - `Routing config`: the config that decides where a message goes, with the file and the key.
     Examples are queue names, URLs, route rules and feature flags.
   - `Error paths`: each retry, dead letter, timeout, error reply and compensation, once more, as a
     list. The flows show where, and the list shows what.
   - `Other systems`: each other system that the service sends to or receives from. Give its name,
     then its handles in backticks. Examples are queue names, endpoints, artifact ids and host names.
8. Conventions and where to look. Write them as fact lines, each in its section of the map:
   - `Conventions`: one line for each of these topics. The cite of a line is one example line of the
     code. A topic with nothing to find is `- <topic>: none found` with no cite.
     - `tests`: where the tests live and what name a test file has, from one test file;
     - `errors`: how the code raises and handles an error on a message path, from one line that does it.
       Examples are an exception type, a `Result` and an error reply;
     - `wiring`: how a dependency reaches a class, from one line that does it. Examples are
       constructor injection, a factory and a global;
     - `naming`: what names the classes or packages of the message path have, from one declaration
       line. Examples are the suffixes `Listener`, `Service` and `Repository`, and one package for
       each feature or for each layer.

     Add a line for any other convention that a new member needs.
   - `Where to look`: one line for each task of a new member. The fact part holds the path where the
     task starts. The path is relative to `<root>`, and it is the first text in backticks of the
     line. The cite is one example line under that path. Write these keys, each once:
     - `add-http`: when `Entry points` has an `http` line with a flow or with `not traced`;
     - `add-listener`: the same for a `listener` line;
     - `add-route`: the same for a `route` line;
     - `add-schedule`: the same for a `schedule` line. A `main` line has no key;
     - `change-routing`: when `Routing config` is not `none found`;
     - `add-transform`: when `Formats and transforms` is not `none found`;
     - `add-event`: when `Events` has an entry. The path is the place where the code declares the event types;
     - `add-test`: when the `test` line of `Shape` is not `none found`.

     Other keys are free. A line of `Where to look` is never `none found`.
9. Not covered. Write one line for each directory or module of the service that you did not read, with
   the reason. Thus the map tells what it does not know.

These reading rules apply to each step:

- Read the source only. Change no file of the source.
- Run no build, no test, no install and no git command that changes the repository.
- Cite only a line that you read from the disk.
- Never copy a password, a token or a key into a snippet or a fact. End the snippet before it, or cite
  a line near it.
- If `.codegraph/` exists in the service, use CodeGraph first. Use `grep -rn` to find a name in the
  files.

The rules do not limit the lines that you read. They limit what leaves the map. An entry point of the
inventory without a line in `Entry points` fails the check. A reason to not trace a flow is one
sentence. It names the flow with the same shape ("the same path as `send`, with the `cancel` type").
Or it says why the entry point is off any message path ("the admin health endpoint reads no message").

An `event` hit without a `type` line, a `payload` line or a dismissal in `Events` fails the check too.

`onboard.py inventory` finds entry points of five kinds and event types of one kind. It reads Java,
Kotlin and Go files, and the YAML and XML files of Camel routes. It skips test trees, `node_modules`,
`target`, `build`, `.git` and `vendor`.

| Kind | Finds |
|---|---|
| `http` | The Spring annotations `@GetMapping`, `@PostMapping`, `@PutMapping`, `@DeleteMapping`, `@PatchMapping` and `@RequestMapping` on a method, the JAX-RS `@Path`, `@MessageMapping` and `@ServerEndpoint`. In Go, a router call whose first argument is a route string, and `http.HandleFunc`. |
| `listener` | The annotations `@JmsListener`, `@RabbitListener`, `@KafkaListener`, `@KafkaHandler`, `@SqsListener`, `@StreamListener`, `@ServiceActivator`, `@InboundChannelAdapter`, `@EventListener`, `@TransactionalEventListener`, `@ExternalTaskSubscription`, `@EventHandler`, `@SagaEventHandler` and `@CommandHandler`, and a class that implements `JavaDelegate`. In Go, the calls `Consume`, `NewReader`, `NewConsumer`, `Subscribe` and `SubscribeTo` with a suffix. |
| `route` | A Camel `from(` in a `RouteBuilder` file, a `- from:` line of a `*.camel.yaml` or `*.camel.yml` file, a `<from uri=…>` element of an XML file, a `routeTemplate` and a `@GrpcService`. In Go, a gRPC call `Register<Service>Server(`. |
| `schedule` | A `@Scheduled` method. In Go, a `cron.` call, `NewTicker` and `time.Tick`. |
| `main` | `public static void main` in Java, `fun main(` in Kotlin and `func main(` in Go. |
| `event` | A class, record, interface or object whose name ends in `Event`, a class that extends `ApplicationEvent` (in Kotlin, `: ApplicationEvent(`), and the annotations `@DomainEvent` and `@Event` on a type. In Go, a `struct` type whose name ends in `Event`. A hit of this kind is a declaration, not an entry point. |

## 3. The map

Write the map to `map.md`. It has this skeleton. Keep the thirteen level-2 sections,
in this order, with these titles. Write `none found` as the one line of an empty section. The skeleton
shows the PlantUML sketches of an onboard map. A course map has the same skeleton with `mermaid` fences
and the node ids of Mermaid.

````
# Map: <id>

## Shape
- <key>: <fact> | <path>:<line> | <snippet>

## Architecture
```plantuml
component "<name>" as <id>
```
- <id>: <fact> | <path>:<line> | <snippet>

## Entry points
- <kind> <name> -> <flow-id> | <path>:<line> | <snippet>
- <kind> <name> -> not traced: <reason> | <path>:<line> | <snippet>
- <kind> <name> -> not an entry point: <reason> | <path>:<line> | <snippet>

## Flows
### <flow-id>: <question>
```plantuml
start
:<label>;
stop
```
- `<label>`: <fact> | <path>:<line> | <snippet>

## State
```plantuml
[*] --> <STATE>
```
- <state>: <fact> | <path>:<line> | <snippet>

## Events
- not an event: `<Name>`: <reason> | <path>:<line> | <snippet>

### <event-name>
- type: <fact> | <path>:<line> | <snippet>
- payload: <fact> | <path>:<line> | <snippet>
- stream: <fact> | <path>:<line> | <snippet>
- emits: `<Component>` <fact> [-> <flow-id>] | <path>:<line> | <snippet>
- consumes: `<Component>` <fact> [-> <flow-id>] | <path>:<line> | <snippet>

## Formats and transforms
## Routing config
## Error paths
## Other systems
- <system>: <handles> | <path>:<line> | <snippet>

## Conventions
- <topic>: <fact> | <path>:<line> | <snippet>

## Where to look
- <key>: `<path>` | <path>:<line> | <snippet>

## Not covered
- <directory or module>: <reason>
````

`<id>` in `# Map: <id>` is the name of the service directory, the last segment of its path. These rules
give the format:

- A fact line is `- <fact> | <path>:<line> | <snippet>`. `<path>` is relative to `<root>`. The snippet
  has at most 12 words, copied verbatim from that line (the cite rules of convention 2 of `SKILL.md`).
  A `Not covered` line has no cite.
- A `Shape` line is `- <key>: <fact> | <path>:<line> | <snippet>`. The keys are those of rule 1 of
  "Explore the service". The `build`, `test` and `run` lines hold one command in backticks, or are
  `none found` with no cite.
- A `Conventions` line is `- <topic>: <fact> | <path>:<line> | <snippet>`. Write a line for each of the
  four topics of rule 8. A line for any other topic that matches `[a-z][a-z0-9_-]*` is free.
- A `Where to look` line is `- <key>: `<path>` | <path>:<line> | <snippet>`. The path is relative to
  `<root>`, and it is the first text in backticks of the line. It is a file or a directory under
  `<root>`. Rule 8 of "Explore the service" gives the keys and the cases for each key.
- A dismissal of `Events` is `- not an event: `<Name>`: <reason> | <path>:<line> | <snippet>`. It stands
  before the first entry. The reason is not empty. Its cite is the line that the inventory found.
- An `Events` entry is a line `### <event-name>` and the keyed lines below it. The `<event-name>` is the
  name exactly as the code writes it. Examples are `OrderPlaced`, `event.document.signature` and
  `order-placed.v2`. Keep its case and its punctuation. The name is unique in the section. On the page, the
  name becomes the anchor `event-<slug>`. To make the `<slug>`, write the name in lowercase. Replace each
  run of characters outside `[a-z0-9]` with `-`. Remove a `-` at the start and at the end. When two names
  give the same `<slug>`, the second gets `-2` at its end and the third gets `-3`. A name with no character
  in `[a-z0-9]` has the slug `e<n>`, where `<n>` is the number of its entry in the section, counted from 1.
- `type` is necessary, once. Its cite is the line that declares the name. That line is the class or
  record, or the constant or string that holds the routing key or the event type. The code of a framework
  event is outside `<root>`. An example is `ApplicationReadyEvent`. Then the cite is the first line of
  source code under the root that names it. A line of a document is not a cite for this. The fact says
  where the type comes from.
- `payload` is optional, once. Use it when the name is not the payload class. An example is a routing key
  that carries `BoxEvent`. Its cite is the declaration of the payload class. When the name is the class,
  write no `payload` line.
- `stream` is necessary, once. The fact says where the event goes: a stream of the event store, a topic, an
  exchange or `in-process`. Use `in-process` for an application event inside one process.
- `emits` is necessary, in one line or more. The cite is the line that publishes, applies, appends or sends
  the event.
- `consumes` is necessary, in one line or more. The cite is the line of the handler method, of the
  `@EventSourcingHandler` or of the subscription. An aggregate that rebuilds its state from the event is a
  consumer.
- A line of `emits` or `consumes` has one of these forms:
  - A component: the first text in backticks is the component name. It becomes a column of the matrix. Use
    the label of a part in `Architecture`. The check does not enforce this. An optional ` -> <flow-id>` ends
    the fact part. It links the line to the flow where the event happens. The flow id exists
    under `Flows`. A tail after ` -> ` that is not a flow id fails in the same way.
  - `outside: <system> `<handle>``: the event comes from a system outside the repository, or goes to it. The
    `<handle>` is the topic, the exchange or the stream. For a framework event, the `<handle>` is the class
    that publishes it (`outside: Spring Boot `SpringApplication``). The cite is the line of the config or
    of the code that names the handle. The `<system>` becomes a column of the matrix.
  - A catch-all consumer. An example is a binding `event.document.*` with a `default` branch that only logs
    and acknowledges. Write one `consumes` line for each key that it receives and does not handle. After the
    component, the fact starts with `ignores:`. The cite is the `default` line. On the page, the mark of such
    a line is `(C)`.
  - `none found`, with no cite: the map found no emitter or no consumer. Write at most one such line for a
    key. Never write it next to another line of the same key.
- `Events` with `none found` holds no entry. It can hold dismissals. An `event` hit still needs a dismissal.
  The cite rules of every fact line apply to the lines of an entry.
- A node fact line starts with the node id and a colon: `- <id>: <fact> | <path>:<line> | <snippet>`.
  Each node of the diagram above it has exactly one such line. Each such line names a node of that
  diagram. In an activity diagram the key is the label in backticks, verbatim:
  `` - `<label>`: <fact> | <path>:<line> | <snippet> ``. The key of a fact line that starts with a
  backtick is the text up to the closing backtick.
- A flow id matches `[a-z][a-z0-9_-]*`. In a Mermaid diagram a node id matches the same pattern. The
  node ids are unique inside one diagram. A subgraph id is not a node.
- In a PlantUML diagram, a component id matches `[a-z][a-z0-9_]*` and a state id matches
  `[A-Za-z_][A-Za-z0-9_]*`. An id outside its pattern fails as `bad id`. A label of an action holds no
  backtick.
- A diagram is one fenced block. In an onboard map its info string is `plantuml`. In a course map its
  info string is `mermaid`, and its first line is `flowchart TD`, `flowchart LR` or `stateDiagram-v2`.
  `Architecture` holds one component diagram. Each `### <flow-id>: <question>` under `Flows` holds one
  activity diagram. `State` holds one state diagram or the line `none found`. In a state diagram, each
  state other than `[*]` has one fact line, with the state name as its key.
- The check reads the kind of a PlantUML fence from its text. It is an activity diagram when its first
  statement is `start`. It is a state diagram when a line starts with `[*]` or `state `. It is a
  component diagram when it declares a part or draws an edge between two ids. A fence of no kind fails
  as `not a PlantUML kind`. A fence of the wrong kind for its place fails as `not activity`,
  `not component` or `not state`.
- A flowchart or an activity diagram has at most 25 nodes. In an activity diagram the nodes are the distinct labels of its
  actions and conditions.
- `Architecture`, `Flows` and `State` can hold the one line `none found` when the source has no code to
  trace. Examples are a docs repository and a config repository. The check accepts `none found` in
  these three sections and applies no diagram rule to them. When a docs source documents a request
  sequence, draw it as a flow. An example is an API guide with "send, then poll". The node cites of
  that flow point to the lines of the docs.
- The `<kind>` of an `Entry points` line is one of the five entry kinds of the table,
  without `event`: `http`, `listener`, `route`, `schedule` or `main`.
- An `Entry points` line ends its fact part with `-> <flow-id>`, `-> not traced: <reason>` or
  `-> not an entry point: <reason>`. Each flow id that it names exists under `Flows`. A reason is not
  empty.
- With `--inventory`, each entry hit of the inventory is the cite of one `Entry points` line. Each `event`
  hit is the cite of a `type` line, a `payload` line or a dismissal of `Events`.
- `Other systems` keeps the shape that `course_discover.py` reads: the handles in backticks in the fact
  part. Keep the title of this section.

When the map is complete, run
`onboard.py check map.md --root <root> --inventory inventory.txt --notation plantuml`. A course map
passes `--notation mermaid`. A fence of the other notation fails as `not plantuml` or `not mermaid`. The
check writes one failure on each line, then `onboard: ok` or `onboard: <n> failures` last. It exits with code
0 when the map passes and 1 when it finds failures. It exits with code 2 when it cannot read the map,
the root or the inventory file.

Fix the cause of each failure line. Run the check again. Repeat until it prints `onboard: ok`.

The prefix of a line tells where the fault is:

| Prefix | Meaning |
|---|---|
| `section: missing <title>` / `section: <title> out of order` | The level-2 skeleton. |
| `diagram <where>: none` / `diagram <where>: not plantuml` / `diagram <where>: not mermaid` / `diagram <where>: not flowchart or stateDiagram-v2` / `diagram <where>: not a PlantUML kind` / `diagram <where>: not activity` / `diagram <where>: not component` / `diagram <where>: not state` / `diagram <where>: action over lines <n>-<m>` / `diagram <where>: style line <n>` / `diagram <where>: if without else line <n>` / `diagram <where>: <n> nodes, more than 25` | A diagram. `<where>` is `architecture`, `state` or the flow id. An action over lines is a `:` line with no `;` on the same line. A style line is one of the lines that the renderer sets. An `if` without else has no `else` line before its `endif`, or never reaches an `endif`. |
| `node <where>/<id>: no fact line` / `node <where>/<label>: flow <id> not in Flows` / `node architecture/<id>: not declared` / `node <where>/<id>: bad id` / `fact <where>/<id>: not a node` / `fact <where>/<id>: two lines` | The node lines and the fact lines. A `see <flow-id>` action names a flow that does not exist, or an id on an edge has no declaration, or an id is outside its pattern. In an activity diagram `<id>` is the label. |
| `cite <section>#<n>: <problem>` | The problems of `cite_check`: the path is not under the root, the line is beyond the end, the snippet is not on that line, or it has more than 12 words. |
| `entry #<n>: unknown kind <kind>` / `entry #<n>: no flow id and no reason` / `entry #<n>: flow <id> not in Flows` | The `Entry points` lines. |
| `event <name>: twice` / `event <name>: missing <key>` / `event <name>: <key> twice` / `event <name> #<n>: unknown key <key>` / `event <name> #<n>: no component in backticks` / `event <name> #<n>: flow <id> not in Flows` / `event <name>: none found beside a line` | The entries of `Events`. |
| `events #<n>: not a dismissal` / `events: none found beside an entry` | A line of `Events` before the first entry that is not a `not an event` line, or a `none found` line in a section with an entry. |
| `inventory <path>:<line>: not in Entry points` / `inventory <path>:<line>: not in Events` | Only with `--inventory`: an inventory line that no `Entry points` line cites, or an `event` line that no `type` line, no `payload` line and no dismissal cites. |
| `shape: missing <key>` / `shape: <key> twice` / `shape #<n>: unknown key <key>` / `shape #<n>: no command in backticks` | The keyed `Shape` lines. |
| `conventions: missing <topic>` / `conventions #<n>: no topic` | The `Conventions` lines. |
| `where: missing <key>` / `where #<n>: no path in backticks` / `where #<n>: <path> not under root` | The `Where to look` lines. |
| `map: cannot read` | The file is not Markdown with a `# Map:` title. The exit code is 2. |

Each other line of the check starts with one of these prefixes too, for example
`fact Other systems#<n>: no handle in backticks`.

The map is for the author, not for a reader, and the lint does not read its prose. Keep each code name
in backticks.

## 4. Plan the sections

The page is Markdown for Confluence. Plan it from the map. These rules of form hold for the whole page:

- Use ATX headings only. The page has one `# ` line, the title. Each other heading is a `## ` line.
- One line is one paragraph. Do not wrap a line by hand.
- A list item starts with `- `. A table is a pipe table with a header row and a `|---|` row. Leave one
  blank line above and below it.
- Fence each command and give the fence an info string (`sh`, `yaml` or `text`). Never put a command
  inline. In prose, put a code name in backticks.
- A diagram is one image line alone on its line, with a blank line above and below it:
  `![<caption>](diagrams/<id>.png)`. The caption is one STE sentence that says what the picture shows.
  The STE lint reads the caption.
- Bold is only for the label of the short answer. Use no HTML, no footnote and no definition list. Put
  no link inside the page: name a section by its heading in words, for example "see the section ...".
  Put a URL in the last section only.

The page has these parts, in this order. The section count follows the flows: never merge flows.

1. `# <question>`: what the service does and why it exists, as a question.
2. The short answer: one paragraph that starts with `**Short answer.**`. It holds two to four sentences
   and at most 70 words. They give the purpose, the runtime kind and the main flows by name, from
   `Shape`. A Russian page also translates this label. The page check accepts any bold text at the start
   of the paragraph.
3. `## What is <service> made of?`: a lead paragraph and the architecture image. Then one paragraph for
   each other system and each store of the diagram.
4. `## How do I build, test and run it?`: a table with one row for each `language` and `framework` line.
   A row gives the name and the version. Then, for `build`, `test` and `run`, in this order, one sentence
   and one fenced block with the command alone. A `none found` line becomes one sentence and no block.
5. `## Where does a message enter?`: a table with one row for each traced or not traced entry point of the
   map. A row gives the kind, the name in backticks, and the question of its flow, or "not traced" with the
   reason.
6. One section for each flow, in map order. Its heading is the question of the flow, verbatim. It holds,
   in this order:
   - a lead paragraph: what comes in and what leaves;
   - the flow image;
   - one paragraph for each condition, which names its outcomes and says why each branch exists;
   - one paragraph for each action that calls another system or writes a store;
   - one sentence for each `see <flow-id>`, which names the section of that flow by its heading.
7. `## Which states does a message go through?`: the state image and one paragraph for each state. Omit
   the section when `State` is `none found`.
8. `## Which events move through <service>?`: a lead paragraph, one sentence that explains the marks, the
   matrix, then one bullet for each event. The matrix is a pipe table. It has one row for each event and
   one column for each component and each outside system. A cell is `E`, `C`, `E C` or `(C)`. The table
   has a last column `gaps` when a `none found` line exists. A bullet gives the payload and the stream.
   It names who emits the event in which flow, and who consumes it in which flow. Omit the section when
   `Events` has no entry.
9. `## Which formats and transforms does it use?`, `## Which config routes a message?`,
   `## What happens on an error?` and `## Which other systems does it talk to?`. The error section is a
   list, and each item names the section of the flow where the error happens. The systems section is a
   table of each system and its handles. Omit each of these sections when its section of the map is
   `none found`.
10. `## How is the code written?`: one paragraph for each `Conventions` line. A `none found` topic is
    one sentence. Omit the section when each line is `none found`.
11. `## Where do I look to change something?`: a table of the task and the path in backticks. Omit the
    section when `Where to look` is `none found`.
12. `## Terms`: a table of the term and its meaning. Write it when the page uses a term that a new
    member of the team does not know.
13. `## Not covered`: one bullet for each `Not covered` line of the map. Add one bullet for each
    not traced entry point, with its reason. Write `none` when there is no bullet.
14. `## About this page`: a table with the subject (the service path), the root, the commit, the dirty
    state, the date and the command (`/explain <path> --as onboard`).

The English headings above are the default. A Russian page translates the fixed headings and keeps the
structure (convention 7 of `SKILL.md`). The headings of the flow sections are always the questions of
the map, verbatim.

## 5. Write the page

Work in the output directory, and do these eight steps in this order:

1. Write `map.md` by "Explore the service" and "The map". Run
   `onboard.py check map.md --root <root> --inventory inventory.txt --notation plantuml`. Fix the cause
   of each failure line. Run the check again until it prints `onboard: ok`.
2. Run `onboard.py diagrams map.md --out diagrams`. Then run `puml.py render diagrams` until it prints
   `plantuml: ok <n> diagrams`. Fix a `plantuml: FAIL` line in the map fence, never in the `.puml` file.
   Then run step 1 and step 2 again.
3. Read each `diagrams/<id>.png` with the Read tool. Look for a cut label, a label over a
   line and a condition without an outcome label. Look for an empty branch and for a false picture of
   the code. Fix the map fence. Then run step 1 and step 2 again.
4. Write `page.md` by "Plan the sections".
5. Run `onboard.py page page.md --map map.md`. Fix the cause of each failure line. Run it again until it
   prints `page: ok`. The check finds these names of the map on the page, verbatim and in any place:
   - the name of each traced or not traced entry point;
   - the name of each event: its `### ` heading in the map;
   - the directory or the module before the first `:` of each `Not covered` line.

   Each failure line of the check starts with one of these prefixes:

   | Prefix | Fix |
   |---|---|
   | `page: no title` / `page: second title` / `page: no short answer` | Start the page with its one `# ` line, the title. Start the next paragraph with the bold label of the short answer. |
   | `diagram <id>: no image line` / `diagram <id>: image line twice` / `flow <id>: no section` / `flow <id>: image outside its section` / `flows: out of map order` | Write one image line for each diagram. Put the image line of a flow under the heading of the flow: its question, verbatim. Keep the flow sections in map order. |
   | `image <path>: not under diagrams/` / `image <path>: not in the map` / `image <path>: no file` / `png <id>: no image line` | Each picture is `diagrams/<id>.png`, and `<id>` is a diagram of the map. Run step 2 for a missing PNG file. Delete a PNG file of no diagram. |
   | `diagram <id>: differs from the map` / `diagram <id>: no puml` / `puml <id>: not in the map` | Run step 2 again. Never edit a `.puml` file. Delete each `.puml` file that `onboard.py diagrams` reports as `stale`. |
   | `entry <name>: not on the page` / `event <name>: not on the page` / `not covered #<n>: not on the page` | Write the name on the page, by the rule above. |
   | `command <key>: not in a code block` / `paragraph <line>: two lines` / `html <line>: tag outside code` / `cite <line>: map line on the page` | Obey the rules of form of "Plan the sections". Put each command alone in a fence. Never put it in backticks in the prose. |

6. Run `python3 <skill-dir>/../ste/scripts/ste_lint.py page.md` until it prints `0 errors`.
7. Read `page.md` three times. First, cover the page below the short answer: does the answer alone
   answer the title? Then cover the prose of the first section: does the architecture picture alone
   support the answer? Last, compare the entry table with `inventory.txt`: each traced or not traced
   entry line of the inventory has a row.
8. Hand off: print the path of `page.md`. When you run for the user directly, run `open <output-dir>`.
   Then the user can take the page and the PNG files. Never run `open` inside a subagent.

## 6. Output directory

The directory is `~/karpathy/out/YYYY-MM-DD-HHMMSS-onboard-<slug>/` (`SKILL.md` convention 5, with the
rung name `onboard`).

| Path | Holds |
|---|---|
| `map.md` | The onboarding map ("The map"). The source of truth of the page and its only evidence. |
| `inventory.txt` | The entry points and the event types that `onboard.py inventory` found. |
| `diagrams/<id>.puml` | One PlantUML diagram: the fence of the map, verbatim, in `@startuml` and `@enduml`. `onboard.py diagrams` writes it. |
| `diagrams/<id>.png` | Its render. `puml.py render` writes it. |
| `page.md` | The onboarding page, Markdown for Confluence. |

`<id>` is `architecture`, `flow-<flow-id>` or `state`. No `index.html`, no snapshots, no `review/`.
