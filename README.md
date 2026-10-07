# Project Chameleon

Project Chameleon retargets structured designs across canvas shapes without replacing their assets or content.

The source of truth for future agents is [`Docs/PROJECT_CONTRACT.md`](Docs/PROJECT_CONTRACT.md). Accepted rationale is in [`Docs/DECISIONS/`](Docs/DECISIONS/); current gaps and external blockers are in [`Docs/STATUS.md`](Docs/STATUS.md); the execution plan is [`Docs/IMPLEMENTATION_ROADMAP.md`](Docs/IMPLEMENTATION_ROADMAP.md).

Repository controls:

- Shared skills: [`skills/`](skills/)
- Harness verifier: `make verify`
- Strict engine preflight: `make preflight`
- Install the versioned Git hook: `make install-hooks`
- Full agent gate: `make agent-check`

The nested `chameleon` engine must be restored before running software tests or
Docker qualification. The verifier reports this state explicitly.

[You have received this identical output 3 times. Re-reading '/Users/gabegaines/workflow/projects/project_chameleon/README.md:raw' will not change it — use a narrower selector (path:A-B), or proceed with the edit.]