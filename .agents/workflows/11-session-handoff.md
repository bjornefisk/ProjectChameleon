---
id: chameleon.workflow.handoff
version: 2.0
owner: current task owner
entry: pause, completion, handoff, or capability loss
exit: resumable record accepted by next owner
---

# 11 — Session handoff

## Purpose

Make work resumable across people, agents, runtimes, and interruptions without relying on hidden chat context.

## Required record

- run/task/issue/PR IDs;
- current role, workflow, gate, and owner;
- goal, acceptance, non-goals, authority/ADR impact;
- changed files/resources and uncommitted state;
- commands/checks run with exact results;
- evidence/artifact paths and claim classifications;
- assumptions, external facts, failures, and checks not run;
- blockers, approvals, rollback, and the next concrete action.

## Procedure

1. Re-read current files/diff and verify the record matches reality.
2. Separate observed results from inference and unverified external facts.
3. Remove secrets, personal data, and unnecessary context.
4. State the next command/owner and the condition that allows it.
5. Publish through [`../templates/handoff.md`](../templates/handoff.md); for multi-agent runs also update [`../templates/agent-run.md`](../templates/agent-run.md).

## Exit gate

A new owner can resume without asking for hidden context, and no claim says a check passed when it was not run.

## Stop conditions

Unexplained dirty state, missing ownership, secret exposure, contradictory evidence, or unresolved destructive action. Preserve the state and escalate.
