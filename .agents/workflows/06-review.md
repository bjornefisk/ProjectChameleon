---
id: chameleon.workflow.review
version: 2.0
owner: reviewer
entry: complete diff and verification handoff
exit: findings dispositioned or explicit review blocker
---

# 06 — Independent review

## Purpose

Challenge correctness, contract compliance, security, test rigor, and blast radius independently of implementation ownership.

## Procedure

1. Load task acceptance, authority, risk class, and complete diff.
2. Inspect callers, serialization, failure paths, fixtures, dependencies, generated artifacts, and review evidence.
3. Test plausible boundary, invalid, ordering, missing-resource, concurrency, rollback, and compatibility cases.
4. Route security/data/supply-chain findings to `security-reviewer` and dependency/release findings to the appropriate owner.
5. Record findings with path/symbol, impact, evidence, severity, owner, and disposition.
6. Re-check fixes; distinguish defects from optional improvements.

## Exit gate

Every acceptance criterion and material risk has a disposition. High-risk findings are fixed or explicitly accepted by the accountable owner with mitigation and revisit date. “No findings” states scope and limitations.

## Stop conditions

Missing context/diff, hidden/generated changes, conflicting authority, unverifiable claim, or request to suppress a finding. Do not rewrite the implementation as a substitute for review.

## Handoff

Use [`../templates/review.md`](../templates/review.md) and [`../checklists/review.md`](../checklists/review.md). Approval here is not release approval.
