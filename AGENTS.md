# Project Chameleon agent instructions

These instructions govern autonomous work in this repository. They describe how to work safely; the behavioral contract remains in the documents named below.

## Authority and mandatory reading order

For every implementation task, read these in order before editing:

1. This file.
2. [`Docs/PROJECT_CONTRACT.md`](Docs/PROJECT_CONTRACT.md) and every **Accepted** ADR in [`Docs/DECISIONS/`](Docs/DECISIONS/): ADR-001 through ADR-012.
3. [`chameleon/chameleon_design_schema_v0.9.json`](chameleon/chameleon_design_schema_v0.9.json).
4. [`Docs/DEPENDENCY_EVIDENCE.md`](Docs/DEPENDENCY_EVIDENCE.md) for pinned/versioned external behavior.
5. [`Docs/STATUS.md`](Docs/STATUS.md) and [`Docs/IMPLEMENTATION_ROADMAP.md`](Docs/IMPLEMENTATION_ROADMAP.md) for the current phase, gaps, blockers, and evidence plan.
6. [`Docs/FINAL_ARCHITECTURE.md`](Docs/FINAL_ARCHITECTURE.md) for the consolidated implementation boundary; it is subordinate to the contract and Accepted ADRs.
7. The files and contract fixtures owned by the task.
8. `chameleon/RULES.md` and the challenge brief only for organizer restrictions, after the higher-priority sources are understood.

The source-of-truth precedence is: `PROJECT_CONTRACT.md` plus Accepted ADRs; ratified schema; pinned project adapter and pinned upstream `cr-renderer`; challenge brief and `chameleon/RULES.md`; fixtures; other proposal/roadmap documents; starter code, comments, and warning-only checks. A lower source never silently overrides a higher one. Resolve a conflict by correcting the lower artifact or recording a superseding ADR, never by guessing or following whichever file was read last.

## Current phase and non-negotiables

Gate 1 renderer/validator qualification is cleared. PR #14's bounded Ticket 06 source-aware routing and column-pivot implementation for Issue #13 is merged into `main`. Tickets 07-08 and four-topology search/ranking remain within accepted bounds. Issue #61's PDF-grounded public Level 3 fix is merged in PR #65 (`6dbbc0a3eaba3090997ad9731a4026677dc6978c`), and the issue is closed. Required native x86_64 `Verify and test` run 39711973748 passed on PR head `33f6fd9`. The repository owner explicitly waived partner review; no partner approval is recorded. Cross-platform parity, organizer-held-out scoring, and release qualification remain unverified. Preserve fixed topology/variant bounds; do not add models, model weights/runtime, CP-SAT, OR-Tools, or unapproved solver scope.

Stage 1 work MUST preserve every source record, ID, count, order, type, immutable field, content, asset reference, and source relationship. Only the target canvas, element `x/y/width/height`, and text `font_size` may change; serialized mutable values must be finite integers. The authoritative validator checks serialized rotated bounds, exact foreground-image ratios, quantized common group transforms, source-separated overlap, renderer-measured text/glyph bounds, and missing-asset preservation. Never generate or replace pixels, hide/remove/shedding records, set opacity to zero, or use zero size as a workaround. If no hard-valid candidate exists, fail closed with the typed status and publish no artifacts; `INCOMPLETE_SEARCH` is not infeasibility.

Do not expand scope into the finale/add-on, user pinning, shedding, copy revision, font substitution, reduced previews, image regeneration/redrawing/inpainting/seam-carving/outpainting, unbounded candidate or font search, held-out scoring, or unapproved schema/API/dependency/runtime changes. Issue #61's only authorized contract changes are the narrow supersessions in ADR-010 through ADR-012. Do not turn a warning-only baseline check into contract evidence or invent resource ceilings; preserve deterministic bounded search, all hard invariants, and the no-model/no-CP-SAT restrictions.

## Shared agent operating system

The repository-wide, provider-neutral agent operating system lives in [`.agents/`](.agents/), starting with [`.agents/README.md`](.agents/README.md). It covers intake, research, planning, implementation, testing, review, security, GitHub/PRs, release, evidence, templates, and handoffs. The capability contract in [`.agents/TOOLING.md`](.agents/TOOLING.md) gives the researcher required web search/fetch access while keeping the Stage 1 product runtime offline. It is process guidance only; the contract and Accepted ADRs below remain authoritative for behavior.

## Specialized agent roles

Project role contracts live in [`.agents/roles/`](.agents/roles/):
- **Lead Orchestrator:** Coordinates bounded role/workflow slices and owns synthesis.
- **Planner:** Scopes features into dependency-ordered vertical slices.
- **Researcher:** Produces source-backed evidence and tracks unverified facts; web search is an explicit required capability.
- **Issue Manager:** Discovers the frontier and validates ticket completion.
- **Implementer:** Executes one owned ticket using test-first development.
- **Verifier:** Runs observable checks and records evidence.
- **Reviewer / Security Reviewer:** Performs contract, runtime, maintainability, visual, and security review.
- **GitHub Maintainer / Release Manager:** Manages issues, branches, commits, PRs, merge, release, and rollback evidence.

The former `Docs/AGENTS/` role tree was migrated into `.agents/roles/`; do not create a second role source of truth.

Shared project skills remain under [`skills/`](skills/):

- `chameleon-contract` — contract-first implementation and review rules.
- `chameleon-testing` — deterministic offline testing at observable seams.
- `chameleon-review` — contract, runtime, test, and layout review criteria.

Install the versioned Git hook with `make install-hooks`. The hook rejects staged
generated artifacts, checks whitespace, and runs `scripts/verify_repository.py`.
Use `make verify` for the non-blocking repository wiring check and `make preflight`
when the nested engine checkout is available and software execution should be
required.

## Work ownership and task brief
Before editing, write a brief (in the task message or handoff) with this shape:

```text
Goal:
Owned files:
Relevant contract sections / ADRs:
Acceptance criteria:
Out of scope:
Verification plan:
```

An agent owns only the files explicitly listed in its brief. Agents MUST NOT edit overlapping files or opportunistically repair a sibling's file. Preserve unexpected user or sibling changes. If the change truly crosses ownership, coordinate a new ownership boundary before editing; do not create a compatibility shim merely to avoid coordination.

Use the named workflows deliberately:

- Use **to-spec** and **to-tickets** to break features into tracer-bullet vertical slices with explicit blocking edges before implementation.
- Use **writing-for-agents** to keep task briefs, instructions, and context pointers sharp, co-located, and free of ambiguity.
- Use **tdd** during coding: write a failing test first that asserts the desired invariant at the highest seam, observe it go red, then write the minimal code to turn it green.
- Use **codebase-design** to ensure modules are deep (powerful capabilities hidden behind narrow, simple interfaces) and to design critical seams twice before settling.
- Use **diagnosing-bugs** for root-cause investigation: reproduce the failure deterministically before attempting any edit; never apply speculative patches.
- Use **code-review** before concluding a ticket: check for contract violations, blast radius, edge cases, and test rigor.
- Use **web-design-guidelines** and **frontend-design** when tuning layout heuristics: optimize visual hierarchy, clean margins, balanced whitespace, and readable typography so renders score high on Adobe's vision evaluator.
- Use **grill-with-docs** only to investigate a genuinely new ambiguity that the authority does not resolve; it is not permission to reopen an Accepted decision.
- Use **documentation-and-adrs** when a durable internal decision is accepted: update the appropriate documentation/ADR and then implement against it.
- Use **source-driven-development** for external or versioned behavior (schema, renderer, dependency, base image, or API): inspect the authoritative source/revision, pin or cite it, and record evidence rather than relying on memory or an unpinned latest version.
## Verification and handoff

Every handoff MUST state changed files, affected contract/ADR sections, exact verification commands run, observed evidence/results, checks not run, blockers, and any ambiguity that requires a future ADR. “Not run” is valid; claiming success without exercising the command is not. During a delegated implementation wave, do not run build/lint/tests/formatters while siblings are editing; the integration owner runs the shared checks once. Do not call a baseline failure contract evidence.

For integration, use the exact smoke sequence recorded in `Docs/STATUS.md`:

```bash
cd chameleon
python -m engine.main
python -m unittest discover -s tests -p 'test_*.py' -v
docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1
```

Record whether each command was run, its exit/result, and the relevant output or artifact (including deterministic render/failure evidence where applicable). An arm64-only run is not Stage 1 evidence. Keep hard-validation evidence separate from soft-quality scoring.

## Unverified external facts

Treat organizer-controlled or environment-dependent claims as **UNVERIFIED EXTERNAL FACTS** until checked against an authoritative source. Current examples are M5 Pro resource limits, model allowlist/size limits, scoring thresholds and target catalogue, font licensing/metadata and final Adobe font availability, clean native-amd64/PNG/native-library/Buildx qualification, and final Adobe deployment topology. Do not invent values, silently convert an external blocker into an internal requirement, or make code depend on an unverified claim. Record the source, date/revision, exact unknown, and impact in the handoff; leave the behavior uncommitted until verified. If verification exposes a new durable internal choice, route it through **documentation-and-adrs** and identify the future ADR rather than guessing.
