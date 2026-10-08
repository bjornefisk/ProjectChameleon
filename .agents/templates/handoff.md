# Handoff

```text
run_id/task_id:
from role/owner:
to role/owner:
workflow/gate:
status: complete | paused | blocked | failed
updated:

Goal/acceptance:
Authority/ADR impact:
Changed files/resources:

Observed checks/results/artifacts:
- command/source | result | evidence path

Unrun checks and limitations:
Assumptions/inferences:
External facts and citations:
Security/data notes:
Failures/blockers/owner:
Rollback/migration:

Next concrete action:
```

A handoff is invalid if it claims a check was run when it was not, omits dirty/unexpected state, or requires hidden chat context to resume.
