# Project Chameleon documentation suite

This directory contains the complete source of truth, architectural blueprints, mathematical specifications, decision records, and execution roadmap for Project Chameleon (Adobe University Hackathon North America 2026).

---

## Authority hierarchy

When reading or implementing this project, follow this strict precedence. A lower-precedence document never silently overrides a higher one:

1. **Normative Behavioral Contract & Accepted ADRs:**  
   [`PROJECT_CONTRACT.md`](PROJECT_CONTRACT.md) and [`DECISIONS/`](DECISIONS/) (ADR-001 through ADR-009).
2. **Ratified Structural Wire Schema:**  
   [`../chameleon/chameleon_design_schema_v0.9.json`](../chameleon/chameleon_design_schema_v0.9.json).
3. **Pinned Renderer Adapter & Upstream Source:**  
   [`../chameleon/renderer/converter/`](../chameleon/renderer/converter/) and `cr-renderer` commit `a17e1fb9a732959dd6c21ae168d5ee09d74bd64f` (documented in [`DEPENDENCY_EVIDENCE.md`](DEPENDENCY_EVIDENCE.md)).
4. **Organizer Restrictions & Brief:**  
   [`CHAMELEONCHALLENGE.md`](CHAMELEONCHALLENGE.md) and [`../chameleon/RULES.md`](../chameleon/RULES.md).
5. **Contract Fixtures:**  
   [`../chameleon/tests/fixtures/contract/`](../chameleon/tests/fixtures/contract/).
6. **Architectural & Algorithmic Guidance:**  
   `PROBLEM.md`, `MATHEMATICAL_CONSTRAINTS.md`, `NEURO_SYMBOLIC_ARCHITECTURE.md`, `COMPUTATIONAL_LAYOUT_SOLVERS.md`, `TYPOGRAPHIC_REFLOW_AND_GROUPING.md`, `OBJECTIVE_EVALUATION_METRICS.md`, `DIFFICULTY_TIERS_AND_FAILURE_MODES.md`, `HERMETIC_RUNTIME_ARCHITECTURE.md`, `ADOBE_EXPRESS_INTERACTIVE_ADDON.md`.
7. **Starter Scaffolding & Warnings:**  
   `../chameleon/README.md`, `../chameleon/FAQ.md`, and baseline code in `../chameleon/engine/resize.py` (explicitly an intentionally nonconforming baseline).

---

## Document map & reading order

### Core contract & project governance (must read first)

| Document | Role | Purpose |
|---|---|---|
| [`PROJECT_CONTRACT.md`](PROJECT_CONTRACT.md) | **Normative Contract** | The binding behavioral specification for the Stage 1 engine: input/output, mutability, geometry invariants, rotated AABB, foreground image ratios, grouping, fail-closed rules, and runtime target. |
| [`DECISION_REGISTER.md`](DECISION_REGISTER.md) | **Governance** | Master index of all architectural decision records, tracking statuses, ratified defaults, and external blockers. |
| [`STATUS.md`](STATUS.md) | **Project Status** | Current execution status, completed gates, known implementation gaps, explicitly unverified external facts, and planned verification commands. |
| [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md) | **Execution Roadmap** | Phased delivery plan from Gate 0 through Gate 7, structuring how agents build and qualify the engine in vertical slices. |
| [`FINAL_ARCHITECTURE.md`](FINAL_ARCHITECTURE.md) | **Consolidated Architecture** | Final implementation-facing summary of the Stage 1 engine, renderer, validator, runtime, search, failure, and finale boundaries. It is subordinate to the contract and Accepted ADRs. |
| [`DEPENDENCY_EVIDENCE.md`](DEPENDENCY_EVIDENCE.md) | **Evidence Record** | Verifiable citations and facts for all external dependencies, renderer commits, base image digests, and runtime libraries. |
| [`AGENT_HARNESS_PLAN.md`](AGENT_HARNESS_PLAN.md) | **Agent Harness** | Blueprint for the automated testing harness, regression corpus, and Makefile commands that guide agent development. |
| [`IMPLEMENTATION/`](IMPLEMENTATION/) | **Implementation Blueprint** | Complete `to-spec` engineering specification, data flow models, and 8 dependency-sequenced tracer-bullet tickets for subagent execution. |
| [`AGENTS/`](AGENTS/) | **Multi-Agent Architecture** | Specifications and operational protocols for the 5 specialized agent personas (Plan, Issue, Implementer, Git, and PR/Review). |

All accepted ADRs reside in [`DECISIONS/`](DECISIONS/):

* **[ADR-001: Source of Truth Hierarchy](DECISIONS/ADR-001-source-of-truth-hierarchy.md)** — Establishes explicit document precedence and conflict-resolution rules.
* **[ADR-002: Stage 1 Schema & Renderer Contract](DECISIONS/ADR-002-stage-1-schema-renderer.md)** — Ratifies the wire schema, API signature `resize(source, target_canvas)`, immutable fields, and pinned `cr-renderer` commit.
* **[ADR-003: Hard Constraints & Fallback](DECISIONS/ADR-003-hard-constraints-and-fallback.md)** — Defines hard validity criteria, integer serialization, image ratio preservation, narrow source-bleed exception, and fail-closed infeasibility.
* **[ADR-004: Stage 1 Runtime & Resource Budget](DECISIONS/ADR-004-stage-1-runtime.md)** — Locks in `linux/amd64` offline container execution, pure CPU-only profile (Rosetta 2 safe, $\le$ 8 cores, $\le$ 8 GB RAM), and dynamic asset resolution from `brand_kit/`.
* **[ADR-005: Separate Stage 1 from Finale](DECISIONS/ADR-005-separate-stage-1-from-finale.md)** — Keeps autonomous Stage 1 strictly separated from finale-only interactive features (pinning, shedding, copy edits) and establishes the local HTTP add-on integration.
* **[ADR-006: Failure Protocol & Feasibility Maximization](DECISIONS/ADR-006-failure-protocol-and-search-status.md)** — Defines internal status taxonomy (`SUCCESS`, `MALFORMED_INPUT`, `INFEASIBLE_LAYOUT`, `INCOMPLETE_SEARCH`, `RUNTIME_IO_FAILURE`), atomic JSON/PNG pair publication, and proactive spatial compression to prevent unproduced files on extreme canvases.
* **[ADR-007: Numeric & Geometry Semantics](DECISIONS/ADR-007-numeric-and-geometry-semantics.md)** — Mandates exact rational calculation ingress, one final round-half-even quantization, exact integer image ratio lattices, uniform group transforms, and positive-area AABB collision.
* **[ADR-008: Typography & Renderer Edge Semantics](DECISIONS/ADR-008-typography-and-renderer-edge-semantics.md)** — Adopts UAX #29 extended grapheme clusters intersected with UAX #14 line-break opportunities, code-point $[start, end)$ style ranges, effective span metrics, overflow rejection, and in-box shape strokes.
* **[ADR-009: Initial Search Strategy & Performance Profile](DECISIONS/ADR-009-initial-search-strategy.md)** — Selects bounded structured candidate search across four topology families with a 0 MB neural weight footprint, < 2.0s CPU latency target, < 500 MB solver RAM, and renderer-in-the-loop hard validation.

### Architectural & technical deep-dives (guidance)

| Document | Focus area | Key takeaways |
|---|---|---|
| [`PROBLEM.md`](PROBLEM.md) | Problem Formulation | Why uniform scaling fails, semantic gap in input data, and mandatory output behaviors. |
| [`MATHEMATICAL_CONSTRAINTS.md`](MATHEMATICAL_CONSTRAINTS.md) | Mathematical Model | Formal equations for rotated AABB containment, image aspect ratio invariance, source-separated non-overlap, and soft readability/contrast targets. |
| [`NEURO_SYMBOLIC_ARCHITECTURE.md`](NEURO_SYMBOLIC_ARCHITECTURE.md) | System Pipeline | Four-stage pipeline: (1) role/relationship inference, (2) layout archetype generation, (3) constraint placement/typography, and (4) serialize, render, and validate. |
| [`COMPUTATIONAL_LAYOUT_SOLVERS.md`](COMPUTATIONAL_LAYOUT_SOLVERS.md) | Solver Paradigms | Evaluates structured search (primary), Kiwi/Cassowary (optional cleanup), CP-SAT (deferred conditional backend), and energy methods. |
| [`TYPOGRAPHIC_REFLOW_AND_GROUPING.md`](TYPOGRAPHIC_REFLOW_AND_GROUPING.md) | Typography & Groups | Font metric measurement, binary-search font sizing within slots, typographic hierarchy preservation, and rigid unit derivation. |
| [`OBJECTIVE_EVALUATION_METRICS.md`](OBJECTIVE_EVALUATION_METRICS.md) | Optimization Proxies | Distinguishes hard validation gates from soft ranking terms (alignment, balance, readability, occlusion, overlap penalty). |
| [`DIFFICULTY_TIERS_AND_FAILURE_MODES.md`](DIFFICULTY_TIERS_AND_FAILURE_MODES.md) | Benchmark Profiles | Level 1 (Warm-up), Level 2 (Core banner with bleed), and Level 3 (Advanced 728x90 leaderboard), detailing adversarial stress modes. |
| [`HERMETIC_RUNTIME_ARCHITECTURE.md`](HERMETIC_RUNTIME_ARCHITECTURE.md) | Container Environment | Offline container requirements, build-time packaging, network isolation, and CPU-only resource bounds. |
| [`ADOBE_EXPRESS_INTERACTIVE_ADDON.md`](ADOBE_EXPRESS_INTERACTIVE_ADDON.md) | Stage 2 Finale | Architecture for the live Adobe Express add-on at Adobe HQ, candidate carousels, pinning, and local HTTP engine integration. |
| [`CHAMELEONCHALLENGE.md`](CHAMELEONCHALLENGE.md) | Historical Challenge Brief | Original competition brief supplied by Adobe, contest structure, glossary, and starter instructions. |

---

## Key technical constraints at a glance

1. **Element preservation:** Output must contain the exact same element IDs, count, order, and immutable visual attributes as the source. Elements must never be deleted, hidden, zero-sized, or replaced.
2. **Pixel integrity:** Zero synthetic pixels. Never regenerate, inpaint, seam-carve, redraw, or replace image content with generative models.
3. **Geometry & image ratios:** Coordinates and dimensions must serialize as finite integers. Non-background images must maintain their exact source aspect ratio via integer lattice points $(k \cdot p, k \cdot q)$, including `fit=fill`.
4. **Rotated containment:** Elements must stay inside the target canvas using rotated axis-aligned bounds (with the sole exception of contract-defined translucent source-bleed shapes).
5. **Grouping & collisions:** Elements sharing a `group_id` move as a rigid unit via a single uniform scale and translation. Elements that were separate in the source must not collide (zero positive-area overlap).
6. **Deterministic typography:** Line breaking uses Unicode grapheme cluster safety; style-runs use $[start, end)$ code-point indexing; font size is quantized to integers; overflowing text causes candidate rejection, never silent truncation.
7. **Proactive spatial compression:** On tight canvases like 728×90, the engine compresses font sizes to the floor (10–12px), scales artwork isotropically, and pivots to horizontal ribbon topologies to ensure scorable, valid layouts rather than failing closed.
8. **Hermetic CPU execution:** Container runs `linux/amd64` offline with `--network none`, budgets $\le$ 8 CPU threads and $\le$ 8 GB RAM, has a 0 MB neural weight footprint, and executes in < 2.0s per design.
