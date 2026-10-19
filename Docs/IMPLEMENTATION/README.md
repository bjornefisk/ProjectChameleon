# Project Chameleon implementation blueprint

This directory houses the complete engineering specification, module architecture, and tracer-bullet ticket sequence for building Project Chameleon.

It is structured using the industry-standard **`to-spec`**, **`to-tickets`**, and **`writing-for-agents`** methodologies so autonomous AI agents have explicit implementation boundaries and dependency-sequenced work.
Use `../FINAL_ARCHITECTURE.md` as the consolidated implementation summary. This directory decomposes that architecture into the executable specification and dependency-sequenced tickets.
Current frontier is PR #14 integration review for bounded Ticket 06 source-aware routing and column-pivot work after Gate 1 clearance. Tickets 01-05 are complete; Ticket 06 implementation, focused/full tests, and sample evidence are recorded, and refreshed-PR corrections for contract-valid large sources, readable-floor font search, and accurate path/status evidence are verified locally. Partner review remains pending on `feat/ticket-06-column-pivot-level2`; Tickets 07-08, full candidate ranking, and held-out evaluation remain later. No merge or release is claimed.

---

## Directory layout

```text
Docs/IMPLEMENTATION/
├── README.md              <- This index and dependency frontier guide
├── SPEC.md                <- Full to-spec engineering specification (User stories, seams, decisions)
└── tickets/               <- 8 tracer-bullet vertical slices with explicit blocking edges
    ├── 01-contract-errors-and-validator.md
    ├── 02-renderer-conformance-and-wrapping.md
    ├── 03-atomic-runner-and-fail-closed.md
    ├── 04-exact-geometry-and-group-transforms.md
    ├── 05-level-1-safe-geometry-solver.md
    ├── 06-column-pivot-and-level-2-solver.md
    ├── 07-horizontal-ribbon-and-level-3-solver.md
    └── 08-candidate-search-ranking-and-offline-docker.md
```

---

## Ticket dependency graph

Agents work the **frontier**: any ticket whose blockers are 100% complete.

```text
[01: Contract Validator] ─────┐
       │                     │
       ▼                     ▼
[03: Atomic Runner]      [02: Renderer Conformance]
       │                     │
       ▼                     │
[04: Exact Geometry] ────────┘
       │
       └─────────────┐
                     ▼
           [05: Level 1 Solver]
                     │ (blocks)
                     ▼
           [06: Level 2 Solver]
                     │ (blocks)
                     ▼
           [07: Level 3 Solver]
                     │ (blocks)
                     ▼
           [08: Macro Search & Docker]
```

---

## Execution summary by ticket

| Ticket | What it delivers | Blocked by |
|---|---|---|
| **01** | `engine/errors.py` & `engine/contract.py` semantic validator oracle | None (can start immediately) |
| **02** | `wrap.py`, `convert.py`, `shapes.py` Unicode & style-run fixes | None (can start immediately) |
| **03** | `staging.py` & `main.py` atomic JSON/PNG pair publication & error isolation | **01** |
| **04** | `geometry/` exact rational math, rotated AABB, and group transforms | **01, 03** |
| **05** | `resize.py` isotropic scaling & near-isomorphic solver (passes Level 1) | **02, 03, 04** |
| **06** | `roles.py` & `column_pivot.py` multi-signal inference (passes Level 2) | **05** |
| **07** | `horizontal_ribbon.py` & spatial compression engine (passes Level 3) | **06** |
| **08** | Complete 12-candidate search, fixed-point ranking & Docker qualification | **07** |

---

## Agent execution rules
1. **Never edit files outside the assigned ticket:** Each ticket owns distinct files and modules.
2. **Never weaken validators:** Tests and validators are the immutable oracle. Code must adapt to pass the validator, never the reverse.
3. **Verify at the highest seam:** Every ticket must verify observable behavior via tests before marking complete.
