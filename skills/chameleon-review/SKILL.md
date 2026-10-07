---
name: chameleon-review
description: Review Project Chameleon changes for contract compliance, test quality, runtime safety, and visual layout risks.
---

# Chameleon review skill

Review the complete diff against `Docs/PROJECT_CONTRACT.md`, not only the changed
function. Check:

1. identity, count, order, immutable fields, and asset preservation;
2. finite integer serialization, post-rounding validation, ratios, rotated AABBs,
   groups, source-aware overlap, and text bounds;
3. fail-closed behavior and atomic JSON/PNG publication;
4. offline `linux/amd64` packaging and absence of unauthorized dependencies;
5. tests at the highest observable seam;
6. generated layout inspection for containment, collisions, hierarchy, and whitespace.

Return `APPROVE` only when the relevant tests and inspection commands were actually
run. Otherwise state exactly what was not run and why. Do not approve a warning-only
baseline check as contract evidence.
