---
id: chameleon.workflow.verify
version: 2.0
owner: verifier
entry: implementation handoff and acceptance matrix
exit: criterion-by-criterion evidence or explicit failure
---

# 05 — Verify behavior and artifacts

## Purpose

Exercise the changed surface in the real available environment and report truthfully.

## Procedure

1. Re-read acceptance, contract hard constraints, and expected failure behavior.
2. Inspect complete diff, tests, fixtures, generated files, and environment assumptions.
3. Run the smallest focused check, then the documented smoke sequence when available.
4. Cover success, boundaries, invalid input, missing assets, serialization, ordering, and fail-closed paths relevant to the task.
5. Inspect output artifacts and logs; ensure no stale or misleading output survived failure.
6. Record command, exit status, relevant output/artifact, environment, and checks not run.
7. Map each criterion to `OBSERVED` evidence, failure, or `UNVERIFIED_EXTERNAL_FACT`; hand off to review.

## Project gate

For Stage 1, keep hard validation separate from soft quality. `make verify` is wiring evidence, not renderer/validator qualification. An arm64-only run is not native-amd64 evidence.

## Stop conditions

Tool/environment failure, nondeterminism, missing required fixture, hard constraint not proved, unsafe test, or request to delete output/hide failure. Preserve the evidence and escalate.

## Handoff

Use [`../templates/handoff.md`](../templates/handoff.md) and [`../checklists/verification.md`](../checklists/verification.md). A verifier does not approve a release by itself.
