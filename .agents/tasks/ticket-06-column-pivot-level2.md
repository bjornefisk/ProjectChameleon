# Task brief

```text
run_id: run-ticket06-docs-20261018
task_id: task-ticket06-column-pivot-level2
request/source: User-authorized Ticket 06 implementation dispatch; GitHub issue #13
owner/role: @bjornefisk / implementer, with @gabegaines24 as partner reviewer
workflow/gate: Review; Gate 1 cleared, bounded Ticket 06 source-aware routing/column-pivot implementation evidence complete
created/updated: 2026-10-18
status: review — implementation evidence complete; partner review pending

Goal / observable outcome:
Align the agent operating system, frontier records, and Ticket 06 dispatch state with the owner-authored transition branch, then record the bounded deterministic implementation slice and its focused evidence. Documentation MUST state that Gate 1 qualification is cleared, Ticket 06 implementation/tests/sample evidence is complete, partner review is pending, and Tickets 07-08, full ranking, and held-out evaluation remain later.

Relevant authority and ADR sections:
AGENTS.md authority order; Docs/PROJECT_CONTRACT.md; Accepted ADR-001 through ADR-009; Docs/STATUS.md; Docs/FINAL_ARCHITECTURE.md; chameleon/chameleon_design_schema_v0.9.json; Docs/DEPENDENCY_EVIDENCE.md. ADR-001 source precedence, ADR-002 wire/mutability boundary, ADR-003 hard constraints and fail-closed behavior, ADR-004 offline runtime/dependency boundary, ADR-005 Stage 1/finale split, ADR-006 typed failures and pair publication, ADR-007 exact numeric/geometry/group rules, ADR-008 renderer/text rules, and ADR-009 bounded deterministic search are preserved.

Owned files/resources:
AGENTS.md; .agents/README.md; .agents/PROJECT_PROFILE.md; .agents/PRODUCTION_STANDARD.md; .agents/roles/implementer.md; .agents/workflows/02-plan.md; Docs/STATUS.md; Docs/IMPLEMENTATION/README.md; Docs/IMPLEMENTATION_ROADMAP.md; Docs/IMPLEMENTATION/tickets/06-column-pivot-and-level-2-solver.md; .agents/tasks/ticket-06-column-pivot-level2.md; .agents/runs/ticket-06-column-pivot-level2.md.
Sibling code slice (not owned here): chameleon/engine/layout/roles.py, chameleon/engine/layout/column_pivot.py, chameleon/engine/layout/__init__.py, chameleon/engine/layout/near_isomorphic.py, chameleon/engine/resize.py, and chameleon/tests/layout/test_level2.py.

Acceptance criteria:
1. Gate 1 cleared, Issue #13 ownership/reviewer, branch provenance (`feat/ticket-06-column-pivot-level2` from `origin/work/pr-12-ready` at `77b3368`), and the active bounded Ticket 06 phase are consistent across the owned frontier and agent docs.
2. Ticket 06 implementation, focused tests, and Level 2 sample evidence are complete; acceptance checks are marked complete only for this bounded implementation slice, while partner review remains pending.
3. The brief and run record contain the task/run IDs, authority, ownership, capabilities, risk, blockers, exact verification plan, integration owner, sibling slice, and no-checks-run statement.
4. Stage 1 invariants and explicit no-model/no-CP-SAT/OR-Tools, no generated/replaced pixels, no shedding/hiding, offline, and fail-closed restrictions remain explicit; no Ticket 07/08, full ranking, or held-out-evaluation scope is authorized.

Hard invariants / failure behavior:
Preserve source identity, immutable fields, finite integer serialization, exact image ratios, rotated bounds, rigid groups, source-separated overlap, text/render bounds, missing assets, offline runtime, and fail-closed behavior. Never generate or replace pixels, remove/shedding records, use opacity-zero or zero-size workarounds, revise copy, substitute fonts, or weaken validators. If no hard-valid candidate exists, preserve typed fail-closed behavior and publish no misleading artifacts.

Out of scope:
Product source and tests for this documentation slice; Ticket 07/08 topology families; full candidate ranking; held-out evaluation; models/model weights/runtime; CP-SAT/OR-Tools; unapproved dependencies/schema/API/runtime changes; finale behavior; source shedding/hiding; copy revision; font substitution; horizontal ribbon; vertical restack; generated/replaced pixels; opacity-zero or zero-size workarounds.

Inputs and prior evidence:
Owner-authored transition branch `origin/work/pr-12-ready` at revision `77b3368` records Gate 1 cleared, Ticket 05 complete, and bounded `INCOMPLETE_SEARCH` accepted for Gate 1. Main reports the Ticket 06 implementation paths, 31 focused tests, 166 full tests, repository checks, expected Level 3 fail-closed behavior, and supplemental arm64-host Docker evidence below. The local artifact hashes are recorded in the run/status records; no native-amd64 qualification, merge, or release is claimed.

Risk/data classification:
High-risk contract/process documentation; repository source-design metadata only; no secrets or personal data. A misleading phase or acceptance claim could authorize out-of-scope implementation, so partner-review and merge/release claims remain pending until evidenced.

Required capabilities:
repo.read, repo.search, repo.edit, repo.write, git.inspect, and bounded documentation inspection. Product checks were not run by this documentation slice; Main supplied observed implementation evidence. Partner review remains unavailable/pending to this slice.

Dependencies/blockers/owners:
No blocker to partner-review dispatch. Gate 1 and Ticket 05 prerequisites are recorded cleared on the transition branch. Product implementation and focused verification are complete. Independent reviewer reported no patch-introduced correctness findings; partner review by @gabegaines24 remains required. Security review found no secrets and recorded bounded relationship materialization, finite font-search cutoffs, and pre-existing unbounded schema/render dimensions as non-blocking risks owned by @bjornefisk.

Verification plan and exact commands:
Observed by Main: focused layout suite — 31 passed; full suite — 166 passed; `python3 scripts/verify_repository.py`, `make verify`, `git diff --check`, and changed-file `py_compile` — passed; `cd chameleon && ../.venv/bin/python -m engine.main` — exit 1 expected, Levels 1-2 `SUCCESS` with pairs and Level 3 `INCOMPLETE_SEARCH` with no pair; Docker Buildx `linux/amd64 --load` — passed with `FromPlatformFlagConstDisallowed`; offline `docker run --network none` — exit 1 expected for Level 3 with Level 1/2 pairs and no Level 3 pair; offline `cr_renderer`/`skia` imports — `imports=ok`. The Docker run used arm64-host emulation and is supplemental, not native-amd64 qualification.

Rollback/migration:
Revert only this documentation/frontier alignment through normal review if authority is superseded. Do not revert or alter sibling product files. Preserve the transition branch evidence and restore the prior phase wording only through explicit change control.

Handoff target:
Main as integration owner; partner reviewer @gabegaines24 is the next owner for independent review and disposition. No merge or release is claimed.
```

## Completion contract

Implementation, focused checks, hard-validation evidence, and independent first review are recorded. This brief remains in review until partner review by @gabegaines24 is complete; the documentation slice does not mark merge or release.
