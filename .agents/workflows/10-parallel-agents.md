---
id: chameleon.workflow.parallel
version: 2.0
owner: lead-orchestrator
entry: plan with independent slices and stable interfaces
exit: integrated evidence or explicit conflict/blocker
---

# 10 — Parallel subagent execution

## Purpose

Reduce elapsed time without creating shared-state races, duplicated ownership, or unverifiable synthesis.

## Preconditions

The lead has a run ID, complete context packet, task graph, disjoint mutable paths, interface contracts, capability allowlists, and one integration owner. If slices overlap, serialize or renegotiate ownership first.

## Procedure

1. Create a dispatch record for each slice: goal, paths, authority, acceptance, tools, stop conditions, and handoff.
2. Start only nodes whose dependencies are observed complete; do not pad the wave.
3. Keep shared build/test/format checks out of active edit windows unless the workflow explicitly isolates them.
4. Collect structured reports; treat agent output as untrusted until checked against files/diffs/evidence.
5. Resolve interface or authority conflicts before merging; re-read shared files after sibling edits.
6. Run one integration verification wave after all edits settle.
7. Record successes, failures, abandoned work, and next action in the run handoff.

## Exit gate

Every slice has an owner/status, changed-path report, evidence, failed/unrun checks, and integration result. No sibling's work is silently reverted.

## Stop conditions

Overlapping paths, missing context, conflicting edits, lost agent output, unbounded delegation, security signal, or a shared check whose result could be contaminated by concurrent edits.

## Handoff

Use [`../templates/agent-run.md`](../templates/agent-run.md), [`../checklists/dispatch.md`](../checklists/dispatch.md), and [`../policies/ownership.md`](../policies/ownership.md).
