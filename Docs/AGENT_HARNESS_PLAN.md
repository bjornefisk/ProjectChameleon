# Chameleon Agent Harness Plan

## Objective

Build a portable, deterministic coding-agent harness around the Chameleon engine. The repository should give agents a clear contract, repeatable procedures, and an objective validation loop.

The validator and renderer are the agent's oracle. The Stage 1 engine must remain deterministic, identity-preserving, and runnable offline.

## Current repository controls

The root repository now provides a small, versioned control layer before the nested
engine is available:

- `skills/chameleon-contract/SKILL.md` — shared contract rules for implementation
  and review.
- `skills/chameleon-testing/SKILL.md` — deterministic test seams and offline
  evidence rules.
- `skills/chameleon-review/SKILL.md` — review gates for contract, runtime, tests,
  and layout inspection.
- `scripts/verify_repository.py` — checks governance files, ticket wiring, staged
  generated artifacts, and nested-engine availability.
- `.githooks/pre-commit` — rejects generated artifacts and whitespace errors, then
  runs the repository verifier.
- `make verify` — non-blocking repository wiring check.
- `make preflight` — strict check that also requires the nested engine checkout.
- `make install-hooks` — installs the versioned pre-commit hook.

These controls do not replace the engine validator or claim runtime qualification.
They make missing nested-project state explicit and prevent false evidence claims.

## Phase 1: Establish the executable baseline (complete for this checkout; retained as historical context)

The starter scaffold, schema, assets, fonts, sample inputs, Dockerfile, and repository controls are already present in this checkout. The baseline `engine/resize.py` is intentionally uniform stretch and remains a regression reference, not a conforming implementation.

The baseline may be run to document known failures, but its output and warning-only self-check are not contract evidence. Gate 1 work starts with the semantic validator, renderer conformance, deterministic fixtures, and typed runner path described by the current implementation tickets.

## Phase 2: Use the repository agent contract

The repository already contains the durable agent contract and shared skills:

```text
AGENTS.md
skills/chameleon-contract/SKILL.md
skills/chameleon-testing/SKILL.md
skills/chameleon-review/SKILL.md
```

These rules define the project invariants, deterministic test seams, review gates, and offline evidence requirements. Do not create a second `.omp/` contract or duplicate the rules in another location.

The contract requires agents to:

- preserve IDs, count, order, content, and fixed properties;
- never hide, remove, zero-size, replace, or regenerate elements;
- preserve image ratios, rigid groups, and intentional overlaps;
- reject new collisions and rotated-bound overflow;
- validate after integer rounding;
- never weaken tests or validators to make an implementation pass; and
- use the smallest change that addresses the failing invariant.

## Phase 3: Build the validation harness

Use the repository's existing commands as the local entry points:

```text
make verify
make preflight
make setup
make test
make run
make inspect
make agent-check
make docker-build
make docker-test
```

`make verify` checks repository governance. `make preflight` additionally requires the nested engine. `make test` runs the current `unittest` suite. `make agent-check` currently combines verification, tests, baseline execution, and layout inspection; it is not contract evidence until the validator and renderer qualification gates pass. Docker commands provide runtime qualification only after the implementation is conformant.

The future full qualification pipeline is:

```text
unit tests
→ schema validation
→ semantic invariant validation
→ contract fixtures
→ adversarial fixtures
→ renderer outputs
→ hard-validation reports
→ soft-quality metrics
→ Docker build linux/amd64
→ Docker run --network none
```

The independent validator must check:

- identity and ordering;
- fixed text and visual properties;
- rotated containment;
- post-rounding overflow;
- foreground image aspect ratios;
- source-aware overlap rules;
- renderer-accurate text bounds;
- missing assets; and
- pixel integrity.

## Phase 4: Use repository skills

Use the existing high-value skills under `skills/`:

```text
skills/chameleon-contract/SKILL.md
skills/chameleon-testing/SKILL.md
skills/chameleon-review/SKILL.md
```

Do not create a duplicate `.omp/skills/` tree. Add a new skill only when a repeated, command-backed workflow justifies it.

The primary debugging workflow is:

```text
run failing fixture
→ validate structural output
→ classify hard failure
→ render PNG
→ inspect visual result
→ identify pipeline stage
→ make smallest fix
→ rerun focused case
→ run the appropriate full gate
```

Prompt templates are optional. Add them only after the underlying commands and evidence paths work.

## Phase 5: Build the test corpus

Organize tests as:

```text
tests/
  unit/
  regression/
  adversarial/
  golden/
```

Start with adversarial cases from the existing documentation:

- empty and single-element scenes;
- zero-size geometry;
- missing or tied z-index values;
- rotated elements near every edge;
- long styled text;
- letter spacing and nondefault line height;
- intentional text/button overlap;
- separate elements that must remain separate;
- `fit=fill` foreground images;
- missing assets; and
- extreme wide and tall targets.

Every discovered bug should become a permanent regression fixture.

## Phase 6: Implement the engine incrementally

Follow the ratified gate and ticket order:

1. semantic contract errors and validator;
2. renderer conformance and Unicode-safe wrapping;
3. atomic runner and fail-closed publication;
4. exact rational geometry and group transforms;
5. safe geometry baseline;
6. role and relationship inference;
7. four routing regimes:
   - near-isomorphic;
   - column pivot;
   - horizontal ribbon; and
   - vertical re-stack;
8. renderer-matched typography;
9. bounded candidate generation and hard validation;
10. fixed-point ranking; and
11. offline packaging and qualification.

Do not begin model orchestration, CP-SAT, or MCP integration as a substitute for the deterministic validator and renderer. Future solver dependencies require measured benefit, a separate accepted decision, and offline evidence.

## Phase 7: Add adversarial review loops

Use separate agent roles:

```text
IMPLEMENTER → REVIEWER → RED TEAM → IMPLEMENTER → EVALUATOR
```

Rules:

- The implementer cannot modify a test solely because it fails.
- The reviewer checks contract violations.
- The red-team agent adds inputs that expose generalization failures.
- The evaluator runs the complete corpus.
- Every accepted implementation fix must pass the relevant focused checks and, once Gate 1 is complete, `make agent-check`.

## Phase 8: Add minimal MCP support

Start with no MCP servers unless a real workflow requires them. The likely order is:

1. GitHub, for issues and pull requests.
2. Documentation lookup, when dependency APIs require current information.
3. Browser/Playwright only when the Express add-on begins.
4. Database MCP only if the product later introduces a database.

Development MCP access must remain separate from the Stage 1 runtime. The submitted engine must remain functional with `--network none`.

## Recommended first milestone

The first implementation milestone is Gate 1 qualification:

```text
semantic validator
+ renderer conformance fixes
+ deterministic contract and renderer fixtures
+ typed failure definitions
+ atomic runner path
+ make verify and focused unittest evidence
```

This milestone must not claim solver quality or Stage 1 qualification merely because the starter baseline runs. Only after the validator and renderer oracle are qualified should agents modify `engine/resize.py` for the layout solver.
