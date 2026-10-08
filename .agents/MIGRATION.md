# Agent-system migration and maintenance

## What moved

The former `Docs/AGENTS/` role tree was retired. The shared operating system now lives under `.agents/` so both collaborators and their subagents load the same contract, capability policy, workflows, evidence forms, and role versions.

The repository boot file remains [`../AGENTS.md`](../AGENTS.md). Project skills remain under [`../skills/`](../skills/), and the project contract/ADRs remain authoritative. `.agents/` coordinates work; it does not replace those sources.

## Adoption sequence

1. Start at [`.agents/README.md`](README.md).
2. Load [`OPERATING_CONTRACT.md`](OPERATING_CONTRACT.md), [`PROJECT_PROFILE.md`](PROJECT_PROFILE.md), and [`TOOLING.md`](TOOLING.md).
3. Load exactly one lead/role/workflow packet for the task.
4. Give the agent a filled [`templates/task-brief.md`](templates/task-brief.md), owned paths, acceptance criteria, and verification plan.
5. Use [`tool-policy.yml`](tool-policy.yml) to map native runtime tools and deny missing capabilities.
6. Record the run in [`templates/agent-run.md`](templates/agent-run.md) for multi-agent work.
7. Require a handoff using [`templates/handoff.md`](templates/handoff.md).

## Runtime adapter requirements

A provider adapter SHOULD:

- prepend the immutable operating contract and project profile;
- expose only the active role's allowed capabilities;
- map `web.search` to the runtime's web-search tool for the researcher;
- preserve tool results as untrusted data;
- persist task/run/evidence IDs across subagents;
- reject paths outside the task scope or missing ownership;
- record tool availability and unrun checks in the handoff.

If the adapter cannot enforce a permission, the role remains a process rule and the run MUST record that limitation. Do not claim that a Markdown file alone enforces isolation.

## Versioning and change control

Treat role, workflow, policy, and tool-permission edits as process changes. Update the file's version metadata, record the reason, run the repository governance and whitespace checks, and review for authority contradictions. A capability expansion requires security review; a contract interpretation change requires an ADR or correction to the lower artifact.

Do not silently preserve aliases to the retired tree. Update callers, links, onboarding, and verifier requirements in one cutover.

## Source lineage

The prompt system was informed by public prompt research recorded in [`research/prompt-lineage.md`](research/prompt-lineage.md). The repository uses original wording and structural adaptations; it does not silently redistribute long source passages or provider-specific tool schemas. Future verbatim imports require source revision, license/attribution review, and a human decision.

## Migration acceptance

- [ ] Both collaborators load the same `.agents` entrypoint.
- [ ] Every role has an owner, capability allowlist, loop, gates, failure behavior, security boundary, evidence, and handoff.
- [ ] Researcher web search is declared and mapped, with citations required.
- [ ] No retired `Docs/AGENTS/` link remains in active docs or verifier requirements.
- [ ] `make verify` and `git diff --check` pass.
