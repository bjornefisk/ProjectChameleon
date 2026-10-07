---
name: chameleon-testing
description: Build deterministic, offline, contract-first tests for Project Chameleon.
---

# Chameleon testing skill

Prefer observable seams in this order:

1. semantic contract validator;
2. renderer conversion and text measurement;
3. `resize(source, target_canvas)`;
4. batch runner and artifact publication;
5. offline Docker execution.

Every test must be deterministic and runnable without runtime network access.
Cover both valid behavior and adversarial cases: empty designs, degenerate records,
rotated bounds, exact image ratios, rigid groups, source-separated collisions,
Unicode clusters, style ranges, line limits, missing assets, and stale outputs.

Never weaken a validator or delete a failing test to make the baseline pass. Keep
hard-validation evidence separate from soft visual-quality scores.

Use the repository entry points where available:

```bash
make test
make inspect
make agent-check
make docker-test
```

If the nested `chameleon` project is unavailable, report that as an environment
blocker instead of replacing the engine with a test double.
