# Computational layout optimization solvers

Retargeting has two separate search problems. The engine must choose a topology and place elements, then rank the valid results by alignment, spacing, hierarchy, balance, whitespace, and readability. Solver choice follows the size and structure of the scene rather than a fixed multi-solver pipeline.

## Linear constraints: Kiwi and Cassowary

Kiwi implements the Cassowary constraint-solving algorithm. It represents geometry as linear equalities and inequalities and is useful for alignment, padding, margin distribution, and centering after the topology is known.

Kiwi cannot choose among left, right, above, and below relationships for an unknown overlap. It also cannot model renderer text measurement or source-aware overlap intent by itself. It is optional. A structured placement pass can handle small scenes without it.

## Constraint programming: OR-Tools CP-SAT

Google OR-Tools CP-SAT handles finite integer domains, Boolean choices, and disjunctive spatial constraints. `AddNoOverlap2D` is useful for pairs that were separate in the source, but it must not be applied blindly to source-intended overlaps or to rigid children inside a group.

For designs with 17 elements or fewer, CP-SAT alone is sufficient for the global placement problem when the candidate slots and text measurements are supplied. A structured search over a small set of archetypes and group placements is also viable. The implementation should prefer the simpler path that maintains the hard checks.

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
| Kiwi or Cassowary | No native topology search | No renderer text measurement | Optional cleanup after topology is fixed |
| OR-Tools CP-SAT | Boolean choices and integer non-overlap constraints | Uses measured slot requirements supplied by the layout pass | Primary global solver for small scenes |
| Structured candidate search | Explicit archetype and slot alternatives | Binary search over measured font sizes | Simple alternative for scenes with 17 elements or fewer |
| MILP or HiGHS | Binary separation variables and continuous coordinates | Piecewise approximations require care | Optional alternative when continuous objectives justify it |
| Nonlinear energy methods | Soft penalties only | Can score continuous aesthetic terms | Offline ranking or refinement after hard validation |

## Practical solver roles

The recommended order is:

1. infer roles, groups, source overlaps, and busy image regions;
2. generate several archetype and emphasis candidates;
3. measure text and image requirements;
4. solve each candidate with CP-SAT or structured search;
5. apply optional Kiwi cleanup without changing topology;
6. render and reject hard failures; and
7. rank the remaining candidates with alignment and spacing terms included.

This keeps the combinatorial decisions explicit and makes the rendered result the final authority on text bounds and contrast.
