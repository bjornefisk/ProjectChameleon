# Project Chameleon status

**Date:** 2026-10-09

**Phase:** Ticket 01 implementation complete; ticket 02 remains not started; Gate 1 qualification remains pending.
**Decision status:** Ticket 01 semantic validation has local contract evidence. Renderer, runner, solver, and runtime qualification remain outside this PR.

## Ground truth now recorded

- `Docs/PROJECT_CONTRACT.md` is the Stage 1 behavioral authority.
- ADR-001 establishes source precedence.
- ADR-002 ratifies the v0.9 design wire shape and pins the project renderer contract.
- ADR-003 separates hard constraints from soft objectives and chooses fail-closed infeasibility handling.
- ADR-004 fixes the initial offline `linux/amd64` runtime target and dependency baseline.
- ADR-005 separates autonomous Stage 1 from finale-only Adobe Express interactions.
- `Docs/DEPENDENCY_EVIDENCE.md` records official-source verification, detected versions, pins, risks, and conformance tests.
- ADR-006 ratifies typed failure statuses, logical JSON/PNG pair publication, and conservative cutoff semantics without adding a failure wire envelope.
- ADR-007 ratifies exact numeric ingress, one round-half-even serialization, rigid group transforms, contract AABBs, and positive-area overlap.
- ADR-008 ratifies Unicode-safe line generation, code-point `[start,end)` style ranges, effective span metrics, overflow rejection, and in-box rectangle/ellipse strokes.
- ADR-009 ratifies bounded deterministic four-topology search, renderer-in-loop hard validation, fixed-point ranking, and no initial model/OR-Tools dependency.
- `Docs/FINAL_ARCHITECTURE.md` consolidates the ratified Stage 1 architecture and finale boundary for implementation; it is subordinate to the contract and Accepted ADRs.

## Resolved contract decisions

| Area | Ratified decision | Evidence |
| --- | --- | --- |
| Authority | Contract/Accepted ADRs > schema > pinned renderer > challenge/rules > fixtures > other proposals > starter code | ADR-001, contract §2 |
| API | `resize(source, target_canvas)` returns a flat design; batch metadata is outside it | ADR-002, contract §3 |
| Mutable fields | Target canvas; element `x/y/width/height`; text `font_size`; all serialized as finite integers | ADR-002, contract §5 |
| Fixed fields | Identity/order/type/rotation/z-order/group/material/text/style/fit/shape fields remain unchanged | ADR-002, contract §5 |
| Text | Adapter-owned deterministic line maps; upstream renderer is explicit-line only; `[start,end)` style runs | ADR-002, contract §6 |
| Images | Exact source box ratio for foreground images, including `fit=fill`; full-canvas `fit=cover` is background-only exception | ADR-003, contract §7 |
| Decoration bleed | Only an already-clipped, translucent, ungrouped shape may keep same-side bleed | ADR-003, contract §7 |
| Empty designs | Valid; output is target canvas plus empty list | ADR-003, schema |
| Infeasible target & fallback | Graceful spatial compression (font floors, isotropic scaling, ribboning) maximizes feasibility on extreme canvases; typed `InfeasibleLayoutError` reserved for mathematically impossible geometry; no misleading JSON/PNG | ADR-003, ADR-006, contract §8 |
| Failure protocol | `SUCCESS`, `MALFORMED_INPUT`, `INFEASIBLE_LAYOUT`, `INCOMPLETE_SEARCH`, and `RUNTIME_IO_FAILURE`; no failed-task artifacts; JSON/PNG committed as a logical pair; nonzero aggregate if any task fails; cutoff is never proof of infeasibility | ADR-006, contract §8 |
| Numeric/geometry | Exact rational ingress; one round-half-even serialization; reduced image-ratio lattice; uniform explicit-group scale plus translation; rotated AABB hard predicate; boundary contact allowed; deterministic background and same-side bleed rules | ADR-007, contract §§5, 7 |
| Typography/renderer | UAX #29 clusters intersected with UAX #14 opportunities; latest-fitting greedy breaks; code-point `[start,end)` runs; effective span metrics; explicit/empty-line accounting; overflow rejection; in-box strokes; no public line map | ADR-008, contract §6 |
| Initial search | Deterministic multi-signal inference; four topology families; at most three source-derived variants per family; renderer-in-loop hard validation; fixed-point ranking; 0 MB neural model footprint; < 2.0s latency target | ADR-009, contract §9 |
| Runtime & hardware | Pinned Python 3.11 `linux/amd64`, runtime `--network none`, CPU-only execution (<= 8 cores, <= 8 GB RAM, Rosetta 2 emulation compatible), dynamic asset/font loading, no current model/OR-Tools requirement | ADR-004, ADR-009 |
| Stage split & finale | Stage 1 is autonomous offline engine; pinning, shedding, copy/font changes, and reduced previews are finale-only; finale add-on communicates with engine via local HTTP service | ADR-005, contract §10 |
## Ratified source-of-truth artifacts

These are contract artifacts, not solver or renderer implementation:

- `chameleon/requirements.txt` pins the initial external compatibility baseline.
- `chameleon/Dockerfile` records the intended Python 3.11.11 Bookworm amd64 image and offline environment defaults.
- `chameleon/chameleon_design_schema_v0.9.json` is no longer provisional, accepts empty designs, and records structural ranges/defaults.
- Contract fixtures live under `chameleon/tests/fixtures/contract/`.
- The Level 2 public sample's style range is corrected to valid end-exclusive `[6, 15)` semantics; this is fixture/source-data correction, not solver implementation.
- Ticket 01's semantic validator and contract tests are implemented at `engine.contract`; the renderer adapter, runner, solver, and full Gate 1 qualification remain pending in later tickets.

## Known implementation gaps before the solver

These are intentionally visible; none is silently promoted to contract behavior:

1. `engine/resize.py` is the documented uniform-stretch baseline and violates image-ratio, group, overlap, rotation, and typography rules.
2. `engine/main.py` has a warning-only self-check that checks unrotated rectangles and ID sets; it is not the contract validator.
3. The renderer adapter's style-run end handling, Unicode-safe wrapping, letter-spacing/style-width measurement, explicit line/max-lines/height enforcement, glyph-bound validation, and rectangle/ellipse stroke behavior need conformance work.
4. The batch runner has no accepted typed-status, cutoff, stale-output, or logical-pair publication path yet, and its default JSON decoding does not preserve numeric tokens for exact ingress.
5. The deterministic role-inference, four-topology candidate search, renderer-in-loop ranking, and held-out evaluation path have not been implemented.
6. The Docker build has no project-owned hash-locked wheelhouse or apt-version lock; the direct compatibility pins are an initial baseline.

## External blockers that remain explicitly unverified

- Whether hidden tasks are guaranteed feasible and how the scorer handles no-output or nonzero task failure.
- Organizer-controlled M5 Pro CPU/RAM/disk/GPU limits.
- Final model allowlist and model-size cap.
- Official scoring threshold details and complete target catalogue.
- Font licenses/embedded metadata and final Adobe Express font availability.
- Clean native-amd64 build, PNG determinism, native-library closure, and Apple Silicon Buildx parity.
- Final Adobe Express deployment/backend topology.

These are not unresolved internal design choices. They require external facts or the implementation/conformance phase.

## Ticket 01 verification record

- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/contract -p 'test_*.py' -v` — 27 tests passed.
- `python3 scripts/verify_repository.py` — passed.
- The suite covers schema/source validation, identity and immutable-field preservation, exact numeric ingress, serialized integer geometry, rotated containment and bleed, image ratios, rigid groups, source-separated collision, text line-box checks, empty/degenerate designs, and typed reason codes.
- The ticket-01 PR tree contains no ticket-02 renderer/wrapping implementation, tests, fixtures, or Unicode data. Ticket 02 remains pending human review and approval.

## Remaining Gate 1 qualification

The following sequence is required for later Gate 1 qualification and is not ticket-01 evidence:

```bash
cd chameleon
python -m engine.main
python -m unittest discover -s tests -p 'test_*.py' -v
docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1
```

The warning-only baseline self-check, renderer goldens/native-library parity, clean native amd64 run, and solver remain outside this PR.
