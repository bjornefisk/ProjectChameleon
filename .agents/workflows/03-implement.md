---
id: chameleon.workflow.implement
version: 2.0
owner: implementer
entry: approved brief, owned paths, and verification plan
exit: changed slice with focused evidence or failed safely
---

# 03 — Implement the owned slice

## Purpose

Make a minimal, contract-preserving change and prove it locally before integration.

## Procedure

1. Confirm path ownership and re-read authority, callers, and current state.
2. Reproduce the relevant behavior or add a meaningful failing test for the uncertain boundary.
3. Edit only owned paths using repository tools; preserve unrelated user/sibling work.
4. Keep serialization, error handling, source identity, and hard validation semantics explicit.
5. Run focused tests/checks, inspect the diff, and exercise success, boundary, and failure cases.
6. Update callers/docs/fixtures and remove obsolete cutover code; do not leave stubs or fake fallbacks.
7. Record commands/results and hand off to verifier/reviewer.

## Exit gate

Acceptance behavior is observable, focused checks are meaningful, changed paths are within ownership, and unrun checks/limitations are explicit.

## Stop conditions

Unexpected changes, contract conflict, missing dependency evidence, hard-validation failure, unsafe command, or inability to prove the requested behavior. Preserve the failure; do not suppress it.

## Handoff

Use [`../templates/handoff.md`](../templates/handoff.md) and [`../checklists/implementation.md`](../checklists/implementation.md). Include source/ADR impact and exact next verification.
