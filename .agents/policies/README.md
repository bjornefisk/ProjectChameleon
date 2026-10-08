# Policy registry

Policies are the durable guardrails beneath the role/workflow layer. They are subordinate to `AGENTS.md`, the project contract, and Accepted ADRs.

- [`authority.md`](authority.md) — precedence and conflict handling.
- [`ownership.md`](ownership.md) — mutable-path ownership and parallel work.
- [`evidence.md`](evidence.md) — claim classes, reproducibility, and handoffs.
- [`security.md`](security.md) — data handling, prompt injection, and defensive review.
- [`dependencies.md`](dependencies.md) — pinned versions, provenance, and source-driven change.
- [`artifacts.md`](artifacts.md) — generated output, provenance, retention, and failure cleanup.

Tool permissions are centralized in [`../TOOLING.md`](../TOOLING.md) and [`../tool-policy.yml`](../tool-policy.yml), not duplicated in prose-only role exceptions.
