---
id: chameleon.workflow.change-control
version: 2.0
owner: lead-orchestrator
entry: proposed process/contract/dependency/runtime change
exit: approved change record or rejected/blocked proposal
---

# 09 — Change control and decision record

## Purpose

Prevent lower-level prompts, convenience patches, or process drift from silently changing project authority or production risk.

## Procedure

1. Classify the proposed change: contract, schema, dependency, runtime, security, process, GitHub, or release.
2. Identify the controlling authority and whether an Accepted ADR or contract correction is required.
3. Research external behavior/licensing/version with citations when relevant.
4. Compare alternatives, compatibility, migration, rollback, testing, security, and ownership.
5. Obtain the required project-owner/reviewer approval before implementation.
6. Update the authoritative document and all affected callers/docs in the same cutover.
7. Run focused verification and record why lower artifacts no longer conflict.

## Exit gate

The decision has owner, date, authority, rationale, chosen/rejected options, impact, migration, rollback, evidence, and review status. No implementation relies on a merely proposed decision.

## Stop conditions

Attempt to reopen an Accepted ADR without new authority, missing owner, unverified external assumption, hidden compatibility shim, or disagreement unresolved by the source precedence.

## Handoff

Use [`../templates/adr.md`](../templates/adr.md), [`../policies/authority.md`](../policies/authority.md), and [`../policies/dependencies.md`](../policies/dependencies.md).
