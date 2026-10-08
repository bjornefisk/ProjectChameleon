---
id: chameleon.workflow.release
version: 2.0
owner: release-manager
entry: reviewed candidate and release scope
exit: qualified release, explicit hold, or rollback
---

# 08 — Release qualification

## Purpose

Qualify an immutable candidate, preserve provenance, publish honest notes, and retain a rollback path.

## Procedure

1. Freeze candidate revision, artifact digest, target platform, and source tree state.
2. Verify required implementation, tests/smoke, hard validation, review, security, dependency, license, and environment evidence.
3. Classify each gap as blocker, accepted risk, or `UNVERIFIED_EXTERNAL_FACT`; obtain owner approval.
4. Check artifact/source/generated-file provenance and reproducibility expectations.
5. Prepare release notes, constraints, known gaps, migration, support owner, and rollback.
6. Perform only approved GitHub/tag/artifact mutation; re-read the resulting state.
7. Publish release record and hand off monitoring/rollback ownership.

## Project gate

`make verify` alone is not Stage 1 qualification. Arm64-only evidence is not native-amd64 evidence. The Stage 1 engine remains offline.

## Exit gate

Immutable candidate ID/digest, all checks/results, approvals, limitations, release state, and rollback are recorded.

## Stop conditions

Digest mismatch, dirty/unexpected tree, missing hard evidence, critical security issue, absent approval, undefined rollback, or unverified licensing/deployment claim.

## Handoff

Use [`../templates/release.md`](../templates/release.md) and [`../checklists/release.md`](../checklists/release.md).
