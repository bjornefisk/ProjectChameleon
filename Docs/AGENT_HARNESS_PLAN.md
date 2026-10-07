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

## Phase 1: Establish the executable baseline

1. Import or clone the official starter structure:
   - `engine/main.py`
   - `engine/resize.py`
   - `requirements.txt`
   - `Dockerfile`
   - schema, assets, fonts, and sample inputs
2. Run the naive baseline locally.
3. Confirm that the renderer produces JSON and PNG outputs.
4. Record baseline failures for all three sample levels.
5. Add a basic `pytest` setup and preserve the baseline as a regression reference.

## Phase 2: Create the agent contract

Add:

```text
AGENTS.md
.omp/
  AGENTS.md
  rules/
    chameleon-contract.md
    python.md
    testing.md
```

`AGENTS.md` should contain the durable project rules:

- Preserve IDs, count, order, content, and fixed properties.
- Never hide, remove, zero-size, replace, or regenerate elements.
- Preserve image ratios and intentional overlaps.
- Reject new collisions and rotated-bound overflow.
- Validate after integer rounding.
- Never weaken tests or validators to make an implementation pass.
- Use the smallest change that addresses the failing invariant.

The OMP-specific file should describe tool usage and workflows rather than repeat the challenge contract.

## Phase 3: Build the validation harness

Create one authoritative command:

```text
make agent-check
```

Recommended pipeline:

```text
unit tests
→ schema validation
→ invariant validation
→ sample fixtures
→ adversarial fixtures
→ render outputs
→ quality metrics
→ Docker build linux/amd64
→ Docker run --network none
```

Add supporting commands:

```text
make test
make test-unit
make test-adversarial
make validate
make render
make eval
make docker-test
```

The validator should independently check:

- identity and ordering;
- fixed text and visual properties;
- rotated containment;
- post-rounding overflow;
- foreground image aspect ratios;
- source-aware overlap rules;
- renderer-accurate text bounds;
- missing assets; and
- pixel integrity.

## Phase 4: Add procedural OMP skills

Create only the high-value skills initially:

```text
.omp/skills/
  run-chameleon/SKILL.md
  validate-layout/SKILL.md
  inspect-render/SKILL.md
  adversarial-test/SKILL.md
  create-regression/SKILL.md
```

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
→ run full agent-check
```

Add prompt templates only after the commands and skills work:

```text
.omp/prompts/
  implement.md
  debug.md
  review.md
  research.md
```

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

Follow the documented build order:

1. Safe geometry baseline.
2. Role and relationship inference.
3. Four routing regimes:
   - near-isomorphic;
   - column pivot;
   - horizontal ribbon; and
   - vertical re-stack.
4. Renderer-matched typography.
5. Candidate generation.
6. Hard validation.
7. Soft ranking.
8. Offline packaging.

Do not begin with model orchestration or MCP integration. The deterministic validator and renderer should be the agent's objective oracle.

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
- Every accepted fix must pass `make agent-check`.

## Phase 8: Add minimal MCP support

Start with no MCP servers unless a real workflow requires them. The likely order is:

1. GitHub, for issues and pull requests.
2. Documentation lookup, when dependency APIs require current information.
3. Browser/Playwright only when the Express add-on begins.
4. Database MCP only if the product later introduces a database.

Development MCP access must remain separate from the Stage 1 runtime. The submitted engine must remain functional with `--network none`.

## Recommended first milestone

The first deliverable should be:

```text
official starter engine imported
+ baseline runnable
+ AGENTS.md
+ validator
+ pytest fixtures
+ Makefile
+ make agent-check passing against the baseline contract
```

Only after that should agents modify `engine/resize.py`.
