# ADR-001: Establish the Project Chameleon source-of-truth hierarchy

## Status

Accepted

## Date

2026-10-06

## Context

The repository contains a challenge brief, `RULES.md`, `FAQ.md`, a schema explicitly labeled provisional, proposed architecture documents, sample inputs, a deliberately incorrect `resize.py`, and a renderer adapter. They disagree about wrapping, off-canvas decoration, missing assets, and the Stage 1/finale boundary. Treating every file as equally authoritative makes the contract undecidable.

## Decision

Use this precedence for Stage 1 behavior:

1. `Docs/PROJECT_CONTRACT.md` and Accepted ADRs.
2. The ratified JSON schema for structural syntax.
3. The pinned project renderer adapter and pinned upstream `cr-renderer` source for delegated pixel behavior.
4. The challenge brief and `chameleon/RULES.md` for organizer-supplied restrictions, as clarified by the contract.
5. Sample inputs as conformance fixtures.
6. Other `Docs/*.md` architecture and roadmap files as proposed guidance.
7. Starter code, comments, and warning-only self-checks. The current resize baseline is not a contract authority.

A conflict is resolved by changing the lower-precedence artifact or writing a superseding ADR. It is never resolved by read order or by silently matching current code.

## Alternatives considered

### Make `RULES.md` supreme

Rejected. It does not define the full request envelope, renderer line behavior, or all fixed fields. It cannot be the sole authority for those decisions.

### Make current code executable truth

Rejected. `engine/resize.py` is explicitly a uniform-stretch baseline, and the self-check omits rotated bounds, duplicate IDs, ratios, and fixed-property comparison.

### Treat all documents equally

Rejected. Contradictions would have no resolution rule and implementation would drift toward whichever document was last edited.

## Consequences

- Future implementation work starts from one contract instead of inferring intent from proposals.
- The schema, renderer revision, fixtures, and validator tests must be updated together when the contract changes.
- Existing architecture documents remain useful design material but are not permission to override the contract.
- A contract change requires an ADR update or a superseding ADR; changing starter behavior alone is insufficient.

## Affected files/schema fields

- `Docs/PROJECT_CONTRACT.md`
- `Docs/DECISIONS/ADR-*.md`
- `chameleon/chameleon_design_schema_v0.9.json`
- `chameleon/RULES.md`, `chameleon/FAQ.md`, and `chameleon/README.md`
- All conformance fixtures and validator tests

## Required validation tests

- Verify the three sample task envelopes validate only after extracting `source` and `target_canvas`.
- Verify a response is checked against the ratified schema and semantic contract, not the baseline self-check alone.
- Verify a deliberately mutated fixed field fails even if the JSON Schema still accepts it.
