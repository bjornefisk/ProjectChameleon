---
id: chameleon.workflow.intake
version: 2.0
owner: lead-orchestrator
entry: user request or external task signal
exit: accepted brief or explicit blocker
---

# 00 — Intake and classification

## Purpose

Turn a request into a bounded, owned task before research or mutation.

## Entry criteria

A user request, issue, handoff, or scheduled task exists. The source may be incomplete; the workflow must distinguish missing information from a tool-discoverable fact.

## Procedure

1. State the desired outcome in observable terms.
2. Load repository authority and identify contract, security, dependency, data, release, and external-fact risks.
3. Identify affected surfaces, mutable paths/resources, current owner, and likely roles.
4. Record acceptance criteria, non-goals, assumptions, required capabilities, and verification commands.
5. Search the repository for current conventions, callers, status, and duplicate work.
6. Classify the task as routine, contract-sensitive, security-sensitive, dependency-sensitive, externally visible, or release-critical.
7. Create [`../templates/task-brief.md`](../templates/task-brief.md) and, for multi-agent work, [`../templates/agent-run.md`](../templates/agent-run.md).
8. Route to research, planning, implementation, review, or incident response.

## Exit gate

The brief names goal, owned paths, authority, acceptance, out-of-scope, capabilities, risk, and verification. A blocker names the missing decision, owner, attempted discovery, and next action.

## Stop conditions

Stop before editing on authority conflict, unsafe or unauthorized request, missing ownership, unclear hard acceptance, secret exposure, or a request outside the project phase. Do not resolve these by silently narrowing scope.

## Evidence and handoff

Record task/run IDs, source request, observed repository state, selected role/workflow, capability availability, and next owner. Use [`../checklists/intake.md`](../checklists/intake.md).
