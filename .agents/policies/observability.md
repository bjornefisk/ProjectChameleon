# Agent-run observability policy

## Run identity

Material work uses a stable `run_id` and `task_id`, plus role, workflow, gate, owner, and source revision. Subagent slices use child IDs linked to the parent.

## Event record

Record state transitions, tool capability availability, bounded tool calls, changed paths, approvals, check results, failures, and handoffs. Do not record private chain-of-thought or sensitive data; record concise decision/evidence summaries.

## Failure taxonomy

Use `product`, `test`, `tool`, `environment`, `authority`, `ownership`, `security`, or `external` categories. Include first observed time/context, attempted recovery, current state, and next owner.

## Resumability

The run record and handoff must be sufficient to resume after agent/runtime loss. Chat history is supplemental. Never mark a run complete when a child report or required gate is missing.

## Maintenance

Process telemetry is for auditability, not silent behavior changes. Any new required event or retention rule is a documented process change and must respect the project's data-handling policy.
