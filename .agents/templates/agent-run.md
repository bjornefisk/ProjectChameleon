# Agent run record

```text
run_id:
parent_task_id:
lead owner/role:
started/updated:
current workflow/gate:
source revision:

Outcome and acceptance:
Authority/ADR impact:
Risk/data classification:
Integration owner:

Capabilities available/unavailable:

Children:
- child_id | role | owned paths | dependency | status | evidence/handoff

Dispatch decisions:

Shared interfaces:

Integration checks:
- command | result | artifact/evidence

Failures/abandoned work/unrun checks:

Security or external-fact notes:

Next concrete action/owner:
```

## Rules

Use one child record per slice. Record why work was parallel-safe, verify child output against repository state, and do not mark the run complete until integration evidence and handoffs exist.
