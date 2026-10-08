---
id: chameleon.workflow.debug
version: 2.0
owner: implementer
entry: reproducible failure or strong observed symptom
exit: root cause fixed and regression proof, or bounded blocker
---

# 04 — Diagnose and repair a failure

## Purpose

Find the root cause before patching. Preserve the first useful failure and prevent a symptom-suppression fix.

## Procedure

1. Capture exact input, environment, command, output, stack/trace, artifact, and expected behavior.
2. Reproduce deterministically; if not reproducible, record repetitions and variables.
3. Read the relevant contract, call graph, serialization boundary, dependency/source behavior, and recent diff.
4. Form one falsifiable hypothesis at a time; use the smallest diagnostic check.
5. Separate product, test, tool, environment, authority, and ownership failures.
6. Add or preserve a regression seam when it catches a plausible consumer-visible boundary.
7. Implement the minimal root-cause fix, run focused and required checks, and inspect failure/rollback paths.

## Exit gate

The report links symptom → root cause → fix → regression evidence. If the cause is external or unverified, it remains a blocker with owner and next observation.

## Stop conditions

No authorization for diagnostic access, unsafe reproduction, secret exposure, nondeterministic evidence without bounded capture, or request to weaken the test/contract.

## Handoff

Use [`../templates/experiment-log.md`](../templates/experiment-log.md) and [`../templates/handoff.md`](../templates/handoff.md). State what was not reproduced and why.
