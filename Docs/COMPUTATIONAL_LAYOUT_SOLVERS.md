# Computational layout optimization solvers

> **Authority Notice:** This document is architectural guidance. The binding Stage 1 behavioral contract is ratified in [PROJECT_CONTRACT.md](PROJECT_CONTRACT.md) and Accepted [ADRs](DECISIONS/). In any conflict, the contract and ADRs govern.
Only bounded structured search is part of the current Stage 1 architecture. Every other solver paradigm below is research guidance, not an implementation dependency; adding one requires measured benefit and an accepted dependency/runtime decision.

Retargeting has two separate search problems. The engine must choose a topology and place elements, then rank the valid results by alignment, spacing, hierarchy, balance, whitespace, and readability. Solver choice follows the size and structure of the scene rather than a fixed multi-solver pipeline.

## Linear constraints: Kiwi and Cassowary

Kiwi implements the Cassowary constraint-solving algorithm. It represents geometry as linear equalities and inequalities and is useful for alignment, padding, margin distribution, and centering after the topology is known.

Kiwi cannot choose among left, right, above, and below relationships for an unknown overlap. It also cannot model renderer text measurement or source-aware overlap intent by itself. It is a possible future cleanup tool only; it is not part of the current dependency baseline and requires an accepted dependency decision before use.

## Constraint programming: OR-Tools CP-SAT

Google OR-Tools CP-SAT handles finite integer domains, Boolean choices, and disjunctive spatial constraints. `AddNoOverlap2D` is useful for pairs that were separate in the source, but it must not be applied blindly to source-intended overlaps or to rigid children inside a group.

Bounded structured candidate search across four topology families is the ratified primary Stage 1 solver (ADR-009). It has a 0 MB neural-weight footprint and CPU-only execution, with a < 2.0s per-design performance target subject to qualification evidence. Google OR-Tools CP-SAT is a deferred conditional alternative that may be evaluated only if held-out benchmarks prove a material coverage gain that justifies the dependency and a separate accepted decision.

Coordinates are rounded intentionally for the integer model. The validator recomputes rotated bounds after rounding and rejects any candidate that crosses the canvas edge.

## Mixed-integer linear programming

Mixed-integer linear programming can keep continuous coordinates while representing separation choices with binary variables and big-M constraints. It is a possible alternative when the objective needs continuous piecewise-linear terms, but it is not required for the small-scene Stage 1 path.

## Continuous energy optimization

Energy-based methods can rank or refine soft qualities such as visual balance, alignment, whitespace, and element flow. Their non-convex search can settle in a poor local arrangement and cannot replace the hard identity, ratio, containment, and overlap checks.

## Objective terms

The solver objective should be evaluated only after hard validation. Useful soft terms include:

- shared left, center, right, top, and bottom axes;
- even gaps between elements that form a source sequence;
- preservation of source hierarchy and relative scale;
- balance of non-background visual mass;
- usable whitespace around text and groups;
- readable font size and contrast against the rendered background; and
- preservation of source-intended overlap relationships.

An alignment reward must never pull apart a `group_id` unit or create a new collision. A balance reward must not force every design to be centered.

## Solver comparison

| Solver paradigm | Disjunctive placement | Typography handling | Appropriate Stage 1 role |
| --- | --- | --- | --- |
| Kiwi or Cassowary | No native topology search | No renderer text measurement | Deferred cleanup option; not a current dependency |
| OR-Tools CP-SAT | Boolean choices and integer non-overlap constraints | Uses measured slot requirements supplied by the layout pass | Deferred conditional solver; evaluate only with benchmark and ADR evidence |
| Structured candidate search | Explicit archetype and slot alternatives across 4 topologies | Binary search over measured font sizes | Primary deterministic Stage 1 solver (ADR-009) |
| MILP or HiGHS | Binary separation variables and continuous coordinates | Piecewise approximations require care | Optional alternative when continuous objectives justify it |
| Nonlinear energy methods | Soft penalties only | Can score continuous aesthetic terms | Offline ranking or refinement after hard validation |

## Practical solver roles

The recommended order is:

1. infer roles, groups, source overlaps, and busy image regions;
2. generate source-derived candidates across the four topology families;
3. measure text and image requirements;
4. serialize candidates once and apply the full hard validator;
5. render every surviving candidate and reject hard failures;
6. rank the remaining candidates with fixed-point alignment, spacing, hierarchy, balance, whitespace, readability, and overlap-preservation terms; and
7. select the stable best candidate or publish the typed failure status.

This keeps combinatorial decisions explicit and makes the rendered result the final authority on text bounds and contrast.
