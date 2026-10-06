# Project Chameleon agent instructions

These instructions govern autonomous work in this repository. They describe how to work safely; the behavioral contract remains in the documents named below.

## Authority and mandatory reading order

For every implementation task, read these in order before editing:

1. This file.
2. [`Docs/PROJECT_CONTRACT.md`](Docs/PROJECT_CONTRACT.md) and every **Accepted** ADR in [`Docs/DECISIONS/`](Docs/DECISIONS/): ADR-001 through ADR-005.
3. [`chameleon/chameleon_design_schema_v0.9.json`](chameleon/chameleon_design_schema_v0.9.json).
4. [`Docs/DEPENDENCY_EVIDENCE.md`](Docs/DEPENDENCY_EVIDENCE.md) for pinned/versioned external behavior.
5. [`Docs/STATUS.md`](Docs/STATUS.md) and [`Docs/IMPLEMENTATION_ROADMAP.md`](Docs/IMPLEMENTATION_ROADMAP.md) for the current phase, gaps, blockers, and evidence plan.
6. The files and contract fixtures owned by the task.
7. `chameleon/RULES.md` and the challenge brief only for organizer restrictions, after the higher-priority sources are understood.

The source-of-truth precedence is: `PROJECT_CONTRACT.md` plus Accepted ADRs; ratified schema; pinned project adapter and pinned upstream `cr-renderer`; challenge brief and `chameleon/RULES.md`; fixtures; other proposal/roadmap documents; starter code, comments, and warning-only checks. A lower source never silently overrides a higher one. Resolve a conflict by correcting the lower artifact or recording a superseding ADR, never by guessing or following whichever file was read last.

## Current phase and non-negotiables

The project is at **Gate 1: renderer and validator qualification, before the solver**. The solver has not started. Do not add a model, model weights/runtime, CP-SAT, OR-Tools, or solver orchestration yet.

Stage 1 work MUST preserve the source identity and contract: every source record, ID, count, order, type, immutable field, content, asset reference, and source relationship remains present. Only the target canvas, element `x/y/width/height`, and text `font_size` may change, and serialized mutable values must be finite integers. Hard validation is authoritative: validate serialized rotated bounds, exact foreground-image ratios, groups and source-separated overlap, text/render bounds, and missing-asset preservation. Never generate or replace pixels, hide/remove/shedding records, set opacity to zero, or use zero size as a workaround. If no hard-valid candidate exists, fail closed with the typed infeasibility path and no misleading output files. See the contract for the complete rules; this summary is not a second contract.

Do not expand scope into the finale/add-on, user pinning, candidate selection, shedding, copy revision, font substitution, reduced previews, image regeneration/redrawing/inpainting/seam-carving/outpainting, or unapproved schema/API/dependency/runtime changes. Do not turn a warning-only baseline check into contract evidence. The known gaps are intentionally visible in `Docs/STATUS.md`, including the uniform-stretch `engine/resize.py` baseline, nonconforming warning-only `engine/main.py` self-check and missing typed infeasibility path, renderer style-run/measurement/max-lines/height/stroke gaps, missing semantic validator, and unqualified Docker/native-amd64/offline path.

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
docker buildx build --platform linux/amd64 -t chameleon-stage1 .
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1
```

Record whether each command was run, its exit/result, and the relevant output or artifact (including deterministic render/failure evidence where applicable). An arm64-only run is not Stage 1 evidence. Keep hard-validation evidence separate from soft-quality scoring.

## Unverified external facts

Treat organizer-controlled or environment-dependent claims as **UNVERIFIED EXTERNAL FACTS** until checked against an authoritative source. Current examples are M5 Pro resource limits, model allowlist/size limits, scoring thresholds and target catalogue, font licensing/metadata and final Adobe font availability, clean native-amd64/PNG/native-library/Buildx qualification, and final Adobe deployment topology. Do not invent values, silently convert an external blocker into an internal requirement, or make code depend on an unverified claim. Record the source, date/revision, exact unknown, and impact in the handoff; leave the behavior uncommitted until verified. If verification exposes a new durable internal choice, route it through **documentation-and-adrs** and identify the future ADR rather than guessing.
