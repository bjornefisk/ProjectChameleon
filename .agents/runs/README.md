# Run records

This directory is the canonical record of Project Chameleon implementation, verification, Docker, and handoff runs.

Keep one durable record per meaningful run. Link to `Docs/STATUS.md` for current project state; do not copy the full status document here.

## Run flow

1. **Intake** — state goal, owner, acceptance, authority, risk, and out-of-scope work.
2. **Snapshot** — record branch, revision, worktree state, environment, dependency versions, and network mode.
3. **Execute** — run the smallest focused check, then the documented integration sequence.
4. **Inspect** — verify JSON, PNG, markers, logs, stale paths, and failure cleanup.
5. **Test** — record focused, full, repository, and runtime checks separately.
6. **Classify** — label each claim `OBSERVED`, `INFERRED`, or `UNVERIFIED_EXTERNAL_FACT`.
7. **Handoff** — state failures, unrun checks, owners, rollback, and the next concrete action.

A run record is complete only when another teammate can reproduce the run without hidden chat context.

## Standard Stage 1 smoke sequence

Run from repository root unless a record states a different worktree or interpreter:

```bash
make verify
make preflight
make docker-build
make docker-test
make inspect
```

For local engine execution, use the available project interpreter:

```bash
make run
```

If Docker, dependencies, or a platform are unavailable, record the exact error. Do not convert an unavailable check into a pass or qualification claim.

## Naming

Use a stable descriptive name:

```text
<scope>-<purpose>-<YYYYMMDD>.md
```

Examples:

- `ticket-06-column-pivot-level2.md`
- `issue-21-png-artifact-conformance.md`
- `main-docker-smoke-20261022.md`

## Required sections

Copy `TEMPLATE.md` for new records. Every record must include:

- run ID, owner, branch, revision, and workflow/gate;
- goal and acceptance criteria;
- authority and ADR impact;
- environment, platform, dependencies, network mode, and inputs;
- exact commands and observed results;
- artifact paths, hashes, and publication state where relevant;
- warnings, failures, unrun checks, and limitations;
- security/data notes;
- next owner and concrete action.

Do not store secrets, credentials, private data, or downloaded source archives in run records.

## Records

| Record | Scope | State |
|---|---|---|
| [`main-docker-smoke-20261022.md`](main-docker-smoke-20261022.md) | Main synchronization and offline Docker sample run | Complete; arm64-host amd64 emulation |
| [`ticket-06-column-pivot-level2.md`](ticket-06-column-pivot-level2.md) | Historical Ticket 06 integration run | Historical; current state is in `Docs/STATUS.md` |
| [`issue-21-png-artifact-conformance.md`](issue-21-png-artifact-conformance.md) | Historical PNG artifact-conformance run | Historical; current state is in `Docs/STATUS.md` |
