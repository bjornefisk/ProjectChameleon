# Evidence and claim policy

## Claim classes

- `OBSERVED`: directly read, executed, or reproduced in the current environment.
- `INFERRED`: conclusion derived from observed facts; name the reasoning link.
- `UNVERIFIED_EXTERNAL_FACT`: dependent on current platform, organizer, deployment, licensing, account, or other external authority not qualified here.

Use the label next to material claims. Never upgrade a class without new evidence.

## Minimum record

Every material result records task/run ID, role/workflow/gate, source or command, revision/environment, input/artifact, result/exit state, limitations, and next owner. External claims add URL, publisher, inspected section, publication/update/retrieval date, and scope.

## Reproducibility

Prefer deterministic fixtures and commands. Record seeds, versions, platform, network mode, relevant configuration, and artifact hashes when they affect the result. A test that only echoes a forwarded value, counts rows, checks source text, or asserts “did not throw” is not meaningful behavior evidence.

## Negative evidence

A failed tool call, missing package, timeout, or unavailable runtime proves an environment/capability limitation—not that the product behavior fails or is absent. Preserve the first useful failure and classify it.

## Handoff

Evidence is complete only when another owner can map acceptance criteria to proof, failure, or explicit unknown. Keep hard validation separate from soft scoring and from process wiring checks.
