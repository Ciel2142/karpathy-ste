# What does shop do and why does it exist?

**Short answer.** shop takes orders over HTTP, charges them and announces them on Kafka. It runs as one Spring Boot application. It has two flows: the order flow and the cancel flow.

## What is shop made of?

shop is one Spring Boot application with an order controller, an orders table and a cancel listener. It talks to the Payments API and to Kafka.

![The order controller reads and writes the orders table, calls the Payments API and sends events to Kafka.](diagrams/architecture.png)

The Payments API is an outside system. The order controller calls it to charge an order.

Kafka carries the `orders.*` topics. The order controller sends the created event to it, and the cancel listener reads the cancel event from it.

The orders table holds the order rows. The order controller and the cancel listener both use it.

## How do I build, test and run it?

| Item | Name | Version |
|---|---|---|
| Language | Java and Kotlin | not set |
| Framework | Spring Boot | 3.3.0 |

Run this command to build the service.

```sh
./gradlew build
```

Run this command to test the service.

```sh
./gradlew test
```

Run this command to start the service.

```sh
./gradlew bootRun
```

## Where does a message enter?

| Kind | Name | Flow |
|---|---|---|
| http | `POST /orders` | What happens to a new order? |
| http | `DELETE /orders/{id}` | How is an order cancelled? |
| listener | `orders.cancel` | How is an order cancelled? |
| http | `GET /orders/{id}` | Not traced: a plain read of one row |
| http | `/metrics` | Not traced: the gateway is not covered |
| listener | `consumer` | Not traced: the gateway is not covered |
| schedule | `ticker every minute` | Not traced: the gateway is not covered |
| route | `ShopServer` | Not traced: the gateway is not covered |
| route | `jms:queue:legacy.in` | Not traced: it only logs |
| route | `kafka:stock.updates` | Not traced: it only logs |
| route | `timer:stock` | Not traced: it has no steps |
| route | `jms:queue:shop.in` | Not traced: it only logs |
| schedule | `StockJobs.refresh hourly` | Not traced: stock is not covered |
| listener | `StockDelegate` | Not traced: stock is not covered |

## What happens to a new order?

A client sends an order to `POST /orders`. The service answers with a 202 and the id, or with a 400.

![An order goes through a limit check and a charge, then the service saves it and sends the created event.](diagrams/flow-order.png)

The controller first checks the total against the limit. An order over the limit gets a 400, and any other order goes on.

The controller then charges the order. A declined charge gets the same 400, and a paid order goes on.

The payments client charges the order at the Payments API.

The controller saves the order row in the orders table.

The controller sends the created event to Kafka, and then it answers with a 202 and the id.

## How is an order cancelled?

The cancel listener reads a cancel event, or a client sends `DELETE /orders/{id}`. The service cancels the order, or it keeps the order.

![The listener keeps a shipped order and sets the status of any other order to CANCELLED.](diagrams/flow-cancel.png)

The listener checks the status of the order. It keeps a shipped order, and any other order gets the status CANCELLED.

The listener saves the order row in the orders table. This is the same save as in the section What happens to a new order?

## Which states does an order go through?

![An order starts as NEW, becomes PAID and then SHIPPED, or it becomes CANCELLED.](diagrams/state.png)

A new order starts in the state NEW.

The state PAID follows the charge.

The state SHIPPED is the last state of a sent order. The listener does not cancel a shipped order.

The cancel listener sets the state CANCELLED.

## Which events move through shop?

Two events move through shop. One stays in the process and one goes through Kafka.

In the table, E marks the component that emits the event and C marks the component that consumes it.

| Event | OrderController | OrderPublisher | OrderProjection | Billing |
|---|---|---|---|---|
| `OrderPlacedEvent` |  | E | C |  |
| `orders.created` | E |  |  | C |

- `OrderPlacedEvent`: it carries a placed order. It is a Spring application event in the process. `OrderPublisher` emits it in the section What happens to a new order? `OrderProjection` consumes it in the same section.
- `orders.created`: it carries the order id as a string. It is a Kafka topic. `OrderController` emits it in the section What happens to a new order? The outside system Billing consumes it.

## Which formats and transforms does it use?

- The service binds order bodies as JSON with Spring.

## Which config routes a message?

- The legacy Camel route sends what it reads to a log.

## What happens on an error?

- An order over the limit gets a 400 with a text body. This happens in the section What happens to a new order?

## Which other systems does it talk to?

| System | Handles |
|---|---|
| Payments | `PaymentsClient` `payments.charge` |
| Kafka | `orders.created` `orders.cancel` |

## How is the code written?

Tests sit under `src/test/java` in the package of the class. A test class has the name of the class with the suffix Test.

An order over the limit gets a 400 through `ResponseEntity`.

A dependency is a private final field of the class.

The name of a class shows its role in the message path, such as Listener or Controller.

## Where do I look to change something?

| Task | Path |
|---|---|
| Add an HTTP entry point | `src/main/java/shop/` |
| Add a listener | `src/main/java/shop/` |
| Add a route | `routes/` |
| Add a schedule | `src/main/kotlin/shop/` |
| Change the routing | `config/` |
| Add a transform | `src/main/java/shop/` |
| Add an event | `src/main/java/shop/` |
| Add a test | `src/test/java/shop/` |

## Terms

| Term | Meaning |
|---|---|
| Entry point | The code where a message enters the service. |
| Flow | The path of one message through the service. |
| Topic | A named Kafka channel for events. |

## Not covered

- `cmd/shop-gw`: the Go gateway. The map lists its entry points and traces none of its flows.
- `GET /orders/{id}`: a plain read of one row
- `/metrics`: the gateway is not covered
- `consumer`: the gateway is not covered
- `ticker every minute`: the gateway is not covered
- `ShopServer`: the gateway is not covered
- `jms:queue:legacy.in`: it only logs
- `kafka:stock.updates`: it only logs
- `timer:stock`: it has no steps
- `jms:queue:shop.in`: it only logs
- `StockJobs.refresh hourly`: stock is not covered
- `StockDelegate`: stock is not covered

## About this page

| Item | Value |
|---|---|
| Subject | `tests/fixtures/onboard/tree` |
| Root | `tests/fixtures/onboard/tree` |
| Commit | none |
| Dirty | no |
| Date | 2026-11-02 |
| Command | `/explain tests/fixtures/onboard/tree --as onboard` |
