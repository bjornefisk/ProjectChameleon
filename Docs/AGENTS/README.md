# Project Chameleon multi-agent operating architecture

This directory defines the specialized agent personas that collaborate to design, implement, review, and qualify Project Chameleon.

---

## Agent roles & responsibilities

```text
               ┌────────────────────────┐
               │      Plan Agent        │  (to-spec, to-tickets, writing-for-agents)
               │ (Scoping & Slicing)    │
               └───────────┬────────────┘
                           │
                           ▼
               ┌────────────────────────┐
               │      Issue Agent       │  (triage, frontier management)
               │ (Frontier & Blockers)  │
               └───────────┬────────────┘
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
┌────────────────────────┐   ┌────────────────────────┐
│  Implementer Agent     │   │     Git Agent          │  (git-workflow, guardrails)
│ (TDD & Deep Modules)   │   │ (Atomic Commits & QA)  │
└────────────┬───────────┘   └────────────────────────┘
             │
             ▼
┌────────────────────────┐
│    PR / Review Agent   │   (code-review, web-design-guidelines)
│ (Contract & Diff Gate) │
└────────────────────────┘
```

---

## Agent roster

| Agent | Specialized role | Primary skills | Core responsibility |
|---|---|---|---|
| **Plan Agent** | Architecture & Scoping | `to-spec`, `to-tickets`, `writing-for-agents` | Synthesizes specs, breaks features into tracer-bullet vertical slices, defines test seams |
| **Issue Agent** | Frontier & Ticket Manager | `to-tickets`, `triage` | Tracks `Docs/IMPLEMENTATION/tickets/`, checks blocking edges, unlocks frontier tickets |
| **Implementer Agent** | TDD & Implementation | `tdd`, `codebase-design`, `implement-spec` | Writes failing tests first, builds minimal passing code, respects single-file ownership |
| **Git Agent** | Versioning & Guardrails | `git-workflow-and-versioning`, `git-guardrails-claude-code` | Manages conventional atomic commits, clean diffs, and branch hygiene |
| **PR / Review Agent** | QA & Design Review | `code-review`, `web-design-guidelines`, `frontend-design` | 5-axis review checking contract compliance, no regression, and layout visualizer output |

---

## Protocol for running agents

1. **Plan Agent** defines the specification (`SPEC.md`) and vertical slice tickets with blocking dependencies (`tickets/NN-*.md`).
2. **Issue Agent** identifies unblocked tickets on the dependency frontier.
3. **Implementer Agent** is dispatched onto a single frontier ticket. It writes a failing test first, then implements minimal passing code, and runs `make test`.
4. **PR / Review Agent** reviews the diff against `PROJECT_CONTRACT.md`, inspects terminal layout outputs via `make inspect`, and verifies all acceptance criteria.
5. **Git Agent** creates an atomic conventional commit for the completed ticket (e.g. `feat(contract): implement semantic validator oracle (ticket 01)`).
6. **Issue Agent** marks the ticket complete and unlocks downstream dependent tickets.
