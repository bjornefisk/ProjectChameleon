# Project Chameleon implementation blueprint

This directory houses the complete engineering specification, module architecture, and tracer-bullet ticket sequence for building Project Chameleon.

It is structured using the industry-standard **`to-spec`**, **`to-tickets`**, and **`writing-for-agents`** methodologies so autonomous AI agents have explicit implementation boundaries and dependency-sequenced work.
Use `../FINAL_ARCHITECTURE.md` as the consolidated implementation summary. This directory decomposes that architecture into the executable specification and dependency-sequenced tickets.
Current frontier is bounded Ticket 08 search/ranking integration after Ticket 07 topology implementation. The engine considers all four topology families, admits only renderer-gated hard-valid candidates, ranks fixed-point quality deterministically, and has local held-out-style evidence. The adversarial Level 3 sample remains a typed fail-closed result; native-amd64, broad organizer-held-out, and release qualification remain unverified. No official merge or release claim is made by this blueprint.

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
           [08: Bounded Search & Ranking]
```

---

## Execution summary by ticket

| Ticket | What it delivers | Dependency/status |
|---|---|---|
| **01** | `engine/errors.py` & `engine/contract.py` semantic validator oracle | None (can start immediately) |
| **02** | `wrap.py`, `convert.py`, `shapes.py` Unicode & style-run fixes | None (can start immediately) |
| **03** | `staging.py` & `main.py` atomic JSON/PNG pair publication & error isolation | **01** |
| **04** | `geometry/` exact rational math, rotated AABB, and group transforms | **01, 03** |
| **05** | `resize.py` isotropic scaling & near-isomorphic solver (passes Level 1) | **02, 03, 04** |
| **06** | `roles.py` & `column_pivot.py` multi-signal inference (passes Level 2) | **05** |
| **07** | `horizontal_ribbon.py` & spatial compression engine (passes Level 3) | **06** |
| **08** | Bounded four-family search, fixed-point ranking, local artifact/held-out evidence, and offline Docker qualification plan | **07** for topology interfaces; bounded integration is present, official/native qualification remains pending |

---

## Agent execution rules
1. **Never edit files outside the assigned ticket:** Each ticket owns distinct files and modules.
2. **Never weaken validators:** Tests and validators are the immutable oracle. Code must adapt to pass the validator, never the reverse.
3. **Verify at the highest seam:** Every ticket must verify observable behavior via tests before marking complete.
