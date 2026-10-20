# SDR: How do we notify the end user of each warrant action?
stage: frame
root: /fixture-root
code: /fixture-root/orchestrator; /fixture-root/executor

## Problem

The orchestrator turns claims into warrants and the executor publishes one event for each warrant action. One source system maps many claims to one warrant, so the event no longer says which claim caused the action.

## Context

- One source system maps many claims to one warrant | orchestrator/ClaimRouter.java:8 | Many claims, one warrant
- Each execution event carries the warrant total and no claim id | executor/WarrantEvents.java:6 | carries the warrant total and no claim id
- Notification per aggregate is a known pattern | https://martinfowler.com/articles/201701-event-driven.html | Event-Carried State Transfer

## Functional requirements

- FR-1: The end user is told about every block, unblock and confiscation | source: user
- FR-2: A notification for a warrant with many claims names the claims behind the action | source: code | orchestrator/ClaimRouter.java:8 | Many claims, one warrant
- FR-3: The end user gets one notification for each action, not one for each claim | source: assumption

## Non-functional requirements

- NFR-1: The notification arrives soon after the action | source: user
- NFR-2: A failed notification never blocks or undoes an action | target: unknown | source: web | https://microservices.io/patterns/data/transactional-outbox.html | transactional outbox

## Constraints

- The executor keeps publishing the same events to its other consumers | source: user

## Non-goals

- Choosing the channel (mail, SMS or push) that carries the notification

## Options

### opt-a: Notify per warrant total

pending

### opt-b: Executor emits one event per claim action

pending

### opt-c: Orchestrator keeps a claim ledger

pending

## Consilium

pending

## Decision

pending

## Open questions

pending

## Not covered

pending
