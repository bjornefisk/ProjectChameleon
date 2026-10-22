# Run record: <scope and purpose>

```text
run_id:
owner/role:
workflow/gate:
started/updated:
branch:
source revision:
worktree state:

Goal/acceptance:

Authority and ADR impact:

Environment/platform/versions/network mode:

Inputs/fixtures/seeds:

Out of scope:
```

## Run flow

1. Intake and acceptance.
2. Branch/revision/environment snapshot.
3. Focused check.
4. Full or integration smoke.
5. Artifact and failure inspection.
6. Evidence classification and handoff.

## Commands and observed results

| Check | Exact command | Result | Evidence/artifact |
|---|---|---|---|
| Branch/input snapshot | `<command>` | `PASS` / `FAIL` / `BLOCKED` | `<output or path>` |
| Focused check | `<command>` | `<result>` | `<output or path>` |
| Integration smoke | `<command>` | `<result>` | `<output or path>` |
| Artifact inspection | `<command>` | `<result>` | `<output or path>` |

Use exact exit status. Separate hard validation, soft quality, and wiring checks.

## Artifacts

- Published files:
- Commit markers/manifests:
- Hashes:
- Stale or partial files:

## Warnings and interpretation

- `OBSERVED`:
- `INFERRED`:
- `UNVERIFIED_EXTERNAL_FACT`:

## Failures and unrun checks

- Failure classification:
- Exact error:
- Checks not run:
- Environment or platform limitation:
- Why the limitation does not prove product behavior:

## Security and data notes

- Secrets or personal data:
- Untrusted inputs or external content:
- Network boundary:

## Decision and handoff

- Decision:
- Rollback/migration:
- Next owner:
- Next concrete action:
