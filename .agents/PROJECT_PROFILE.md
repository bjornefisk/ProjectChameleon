# Project Chameleon agent profile

This file supplies repository-specific context to the generic operating contract. It does not override `AGENTS.md`, the project contract, or Accepted ADRs.

## Authority map

Read in this order:

1. [`../AGENTS.md`](../AGENTS.md);
2. [`../Docs/PROJECT_CONTRACT.md`](../Docs/PROJECT_CONTRACT.md) and Accepted ADR-001 through ADR-012;
3. [`../chameleon/chameleon_design_schema_v0.9.json`](../chameleon/chameleon_design_schema_v0.9.json);
4. [`../Docs/DEPENDENCY_EVIDENCE.md`](../Docs/DEPENDENCY_EVIDENCE.md);
5. [`../Docs/STATUS.md`](../Docs/STATUS.md) and [`../Docs/IMPLEMENTATION_ROADMAP.md`](../Docs/IMPLEMENTATION_ROADMAP.md);
6. [`../Docs/FINAL_ARCHITECTURE.md`](../Docs/FINAL_ARCHITECTURE.md);
7. task-owned source, tests, and fixtures;
8. [`../chameleon/RULES.md`](../chameleon/RULES.md) and the challenge brief.

The contract plus Accepted ADRs win conflicts. Starter comments, warning-only checks, and this profile never silently redefine authority.

## Current phase

PR #14's bounded Ticket 06 source-aware routing and column-pivot implementation is merged into `main`. Tickets 07-08 and four-topology search/ranking are implemented within their accepted bounds. Issue #61's PDF-grounded public Level 3 fix produces a hard-valid pair in repeated local tests under Accepted ADR-010 through ADR-012. Maintainer review and native-amd64 CI for the issue branch remain pending; cross-platform parity, organizer-held-out scoring, and release qualification remain unverified.

Stage 1 MUST preserve source identity, IDs, counts, order, types, immutable fields, content, assets, and source relationships. Only target canvas dimensions, element geometry, and text `font_size` may change; serialized mutable values must be finite integers. Hard validation is authoritative for rotated bounds, exact foreground-image ratios, groups and source-separated overlap, text/render bounds, and missing assets. Invalid candidates fail closed without misleading output files.

Do not add models, model weights/runtime, CP-SAT, OR-Tools, solver dependencies, unbounded candidate/font search, shedding/removal, opacity-zero or zero-size workarounds, pixel generation/replacement, copy revision, font substitution, reduced previews, invented resource ceilings, or unapproved schema/API/dependency/runtime changes. The only Issue #61 contract changes are the narrow scopes accepted in ADR-010 through ADR-012.

## Role routing

| Need | Role | Primary output |
|---|---|---|
| Coordinate a multi-step task | [`roles/lead-orchestrator.md`](roles/lead-orchestrator.md) | run record and dispatch plan |
| Clarify scope and acceptance | [`roles/planner.md`](roles/planner.md) | spec/plan |
| Establish external facts | [`roles/researcher.md`](roles/researcher.md) | cited research note |
| Manage tickets/frontier | [`roles/issue-manager.md`](roles/issue-manager.md) | issue/ticket state |
| Implement an owned slice | [`roles/implementer.md`](roles/implementer.md) | source/docs/tests |
| Exercise behavior | [`roles/verifier.md`](roles/verifier.md) | verification record |
| Find correctness gaps | [`roles/reviewer.md`](roles/reviewer.md) | review findings |
| Find security/data risks | [`roles/security-reviewer.md`](roles/security-reviewer.md) | threat findings |
| Manage GitHub state | [`roles/github-maintainer.md`](roles/github-maintainer.md) | issue/PR metadata |
| Qualify a release | [`roles/release-manager.md`](roles/release-manager.md) | release record |

## Capability boundary

The role permissions are declared in [`TOOLING.md`](TOOLING.md) and [`tool-policy.yml`](tool-policy.yml). The researcher has required `web.search` and may use URL fetch/browser tools for source-backed research. That agent access is not product runtime access: the Stage 1 engine remains offline and the integration smoke sequence includes `--network none`.

No documentation can grant a runtime capability that the adapter does not expose. A missing web tool is a recorded blocker, not a reason to invent current facts.

## Verification commands

Use the exact sequence in `../Docs/STATUS.md` when the nested engine and Docker qualification are available:

```bash
cd chameleon
python -m engine.main
python -m unittest discover -s tests -p 'test_*.py' -v
docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1
```

`make verify` checks repository wiring and governance. It is not a substitute for hard renderer/validator evidence. An arm64-only run is not Stage 1 evidence.

## Evidence and external facts

Every handoff records exact commands, outputs/artifacts, checks not run, and limitations. Keep hard-validation evidence separate from soft-quality scoring. M5 Pro limits, model allowlists, scoring thresholds, target catalogues, font licensing/availability, native-amd64 qualification, and final deployment topology remain `UNVERIFIED_EXTERNAL_FACT` until checked against an authoritative source.

## Process invariants

- One agent owns a mutable path at a time.
- Parallel work must have disjoint paths and explicit interfaces.
- Research writes evidence artifacts, not implementation, unless ownership is reassigned.
- GitHub/release mutations require their dedicated role and approval gate.
- Every new durable process rule updates the relevant `.agents` file and its verification checklist.
