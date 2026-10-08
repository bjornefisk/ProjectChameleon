---
id: chameleon.workflow.plan
version: 2.0
owner: planner
entry: accepted intake and available authority
exit: approved implementable slice or blocker
---

# 02 — Plan the vertical slice

## Purpose

Choose the smallest complete design that satisfies the request and is testable at an observable seam.

## Procedure

1. Read the intake brief and all relevant authority/cited research.
2. Map current behavior, public interfaces, callers, serialization, fixtures, and failure paths.
3. Write goal, non-goals, invariants, alternatives, acceptance, and rollback.
4. Define exact owned files/resources and disjoint dependency edges.
5. Select permanent tests or a throwaway smoke scenario; include boundary and failure cases.
6. Identify security, dependency, GitHub, release, and external-fact gates.
7. Create or update spec/ticket; request approval only when a decision is genuinely not resolved by authority.

## Exit gate

The implementer has a bounded task packet, explicit capability set, first action, acceptance mapping, and verification command. No plan may add solver/runtime/dependency scope against the current phase.

## Stop conditions

Unresolved authority/ownership, missing acceptance, unsafe design, unverified external prerequisite, or cross-slice interface without an owner. Escalate; do not start speculative coding.

## Handoff

Use [`../templates/spec.md`](../templates/spec.md) and [`../templates/task-brief.md`](../templates/task-brief.md), then hand to `implementer` or back to `researcher` with a precise question.
