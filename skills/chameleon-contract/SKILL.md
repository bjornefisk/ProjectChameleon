---
name: chameleon-contract
description: Apply Project Chameleon's Stage 1 contract when designing, implementing, testing, or reviewing layout changes.
---

# Chameleon contract skill

Read `Docs/PROJECT_CONTRACT.md` and the accepted ADRs before changing behavior.
Treat the contract as authoritative over starter code, samples, and proposals.

Required invariants:

- preserve source IDs, count, order, types, content, assets, and immutable fields;
- change only target canvas geometry, element geometry, and text `font_size`;
- serialize mutable values as finite integers and validate after serialization;
- preserve foreground image ratios, rigid groups, intentional overlap, and missing assets;
- validate rotated bounds, source-separated overlap, and actual rendered text bounds;
- fail closed without misleading JSON/PNG when no hard-valid candidate exists;
- keep Stage 1 offline, deterministic, CPU-only, and free of model/CP-SAT changes
  unless a later accepted decision authorizes them.

For implementation work, use the ticket's owned-file boundary and write a failing
highest-seam test before implementation code.
