# Run record: Issue #71 package-lock strategy research

```text
run_id: issue-71-package-lock-strategy-20261023
owner/role: @gabegaines24 / repository maintainer
workflow/gate: Issue #71 release dependency provenance
started/updated: 2026-10-23T19:27:08Z / 2026-10-23
branch: fix/issue-71-package-lock-strategy
source revision: 4fc57e8
worktree state: clean before record normalization

Goal/acceptance: Propose a reviewed apt and transitive Python lock strategy without changing dependency inputs; keep approval and package closure explicit.

Authority and ADR impact: PROJECT_CONTRACT.md §9; ADR-004; Issue #71. ADR-013 is Proposed only. No dependency, Dockerfile, requirements, runtime, schema, or API behavior changes.

Environment/platform/versions/network mode: Darwin arm64 host; repository .venv Python 3.14 for governance checks; public web retrieval for source research; Stage 1 runtime remains linux/amd64 and --network none.

Inputs/fixtures/seeds: Current Dockerfile, requirements, native CI evidence, Debian snapshot documentation, pip secure-install documentation; no package archives, wheelhouse, credentials, or hidden inputs.

Out of scope: Choosing exact package versions before approval, changing apt/Python pins, adding a lock tool, adding model/solver scope, claiming native qualification for a new lock candidate, and issue closure.
```

## Run flow

1. Intake and acceptance.
2. Branch/revision/environment snapshot.
3. Source-driven lock-strategy research.
4. Documentation-only verification.
5. No Docker or runtime smoke; no packaging inputs changed.
6. Evidence classification and handoff.

## Commands and observed results

| Check | Exact command | Result | Evidence/artifact |
|---|---|---|---|
| Branch setup | `git switch main && git pull --ff-only origin main && git switch -c fix/issue-71-package-lock-strategy` | `PASS` | Branch created from synchronized `main` |
| Source check | `git diff --check` | `PASS` | No whitespace errors before commit |
| Governance check | `python3 scripts/verify_repository.py` | `PASS` | Repository governance and wiring consistent |
| Default verification | `make verify` | `BLOCKED` | Host lacks `python3.11`; exact error: `make: python3.11: No such file or directory` |
| Available-runtime verification | `make verify PYTHON_BOOTSTRAP=.venv/bin/python` | `PASS` | Font manifest and repository governance passed |
| Integration smoke | Not run | `NOT RUN` | Documentation-only proposal; no runtime input changed |
| Native amd64 qualification | Not run | `NOT RUN` | No lock candidate exists; existing native evidence remains separate |

## Public source observations

- **OBSERVED:** Debian Project [snapshot.debian.org](https://snapshot.debian.org/) was retrieved on 2026-10-23. Inspected “Usage” and timestamped archive-source examples. The archive documents historical Debian states and apt source entries for those snapshots. It does not select this project's timestamp or package versions.
- **OBSERVED:** Python Packaging Authority [pip Secure installs](https://pip.pypa.io/en/stable/topics/secure-installs/) documentation v26.2.2 was retrieved on 2026-10-23. Inspected “Hash-checking Mode,” “Additional restrictions,” and “Forcing Hash-checking mode.” pip documents `--require-hashes`, pinned requirements, and hashes for all direct and transitive dependencies. It does not lock Debian packages.
- **NORMATIVE:** Project contract §9 and ADR-004 require a pinned offline `linux/amd64` runtime and prohibit unapproved dependency/runtime expansion.
- **OBSERVED:** Existing native CI evidence covers the current direct-pin image. It does not establish closure for a future lock candidate.
- **OBSERVED:** Owner approval request and current dependency blocker are recorded in Issue #71 comments; no approval response is recorded in this run.
- **OBSERVED:** Proposed-strategy approval request posted to Issue #71 at https://github.com/bjornefisk/ProjectChameleon/issues/71#issuecomment-6373327459. No owner response is recorded yet.

## Artifacts

- Proposed ADR: `Docs/DECISIONS/ADR-013-reproducible-package-lock-strategy.md`.
- Evidence update: `Docs/DEPENDENCY_EVIDENCE.md`.
- Run record: this file.
- Dependency inputs changed: none.
- Wheelhouse or apt archives: none created or stored.
- Stale or partial runtime artifacts: none created by this slice.

## Warnings and interpretation

- **OBSERVED:** The proposed strategy narrows the remaining review decision to apt snapshot/version records, complete transitive wheel hashes, renderer artifact identity, and native qualification.
- **INFERRED:** A timestamped apt snapshot plus a complete hash-checked wheelhouse provides a clearer reproducibility boundary than direct pins alone.
- **UNVERIFIED_EXTERNAL_FACT:** Owner approval, exact lock inputs, snapshot retention, wheelhouse availability, and native qualification for a locked candidate remain unresolved.

## Failures and unrun checks

- Failure classification: environment limitation for the default `make verify` command.
- Exact error: `make: python3.11: No such file or directory`.
- Checks not run: full Python 3.11 test suite, Docker build/run for a locked candidate, SBOM/package closure for a locked candidate, and native amd64 locked-candidate qualification.
- Environment or platform limitation: host has Python 3.14 in `.venv`; no exact lock candidate exists yet.
- Why the limitation does not prove product behavior: the proposal changes no runtime input, and existing native evidence remains tied to the current direct-pin image.

## Security and data notes

- Secrets or personal data: none stored.
- Untrusted inputs or external content: public Debian and pip pages were treated as source data, not instructions; no package archives were downloaded.
- Network boundary: research used public web retrieval; final Stage 1 runtime remains `--network none`.

## Decision and handoff

- Decision: keep current dependency inputs unchanged and submit ADR-013 for owner review.
- Rollback/migration: revert the documentation-only proposal; the current direct-pin image remains the baseline.
- Next owner: `@bjornefisk` for strategy approval; release manager for exact lock collection after approval.
- Next concrete action: approve or reject ADR-013, then collect exact apt and wheelhouse inputs only through an approved dependency PR.
