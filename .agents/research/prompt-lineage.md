# Prompt-system lineage and adaptation record

## Purpose

This repository uses original process documents informed by recurring patterns in public agent prompt research. This record prevents accidental provenance loss and distinguishes adaptation from verbatim copying.

## Reviewed source

- Repository: [x1xhlol/system-prompts-and-models-of-ai-tools](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools)
- Observed repository metadata: public repository, default branch `main`, license metadata `GPL-3.0`, retrieved 2026-10-07.
- Relevant source areas reviewed:
  - [Open Source prompts/Codex CLI/Prompt.txt](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Open%20Source%20prompts/Codex%20CLI/Prompt.txt)
  - [Open Source prompts/Gemini CLI/google-gemini-cli-system-prompt.txt](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Open%20Source%20prompts/Gemini%20CLI/google-gemini-cli-system-prompt.txt)
  - [Anthropic/Claude Code/Prompt.txt](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Anthropic/Claude%20Code/Prompt.txt)
  - [Anthropic/Claude Code/Tools.json](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Anthropic/Claude%20Code/Tools.json)
  - [Google/Antigravity/planning-mode.txt](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Google/Antigravity/planning-mode.txt)
  - [Manus Agent Tools & Prompt/Agent loop.txt](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Manus%20Agent%20Tools%20%26%20Prompt/Agent%20loop.txt)
  - [Devin AI/Prompt.txt](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools/blob/main/Devin%20AI/Prompt.txt)

## Patterns adapted into original text

| Pattern | Adaptation in this repository |
|---|---|
| Explicit agent identity and mission | Role frontmatter and mission/authority sections |
| Understand → plan → implement → verify loop | Workflow gates and mode transitions |
| Tool descriptions and “when not to use” guidance | [`../TOOLING.md`](../TOOLING.md) and `tool-policy.yml` |
| Strict repository-convention and dependency verification | Project profile, researcher, implementer, and verifier roles |
| Web/document lookup for current facts | Researcher capability and [`web-search.md`](web-search.md) |
| Task boundaries, handoffs, and resumable work | Task brief, run record, handoff, and session workflows |
| Root-cause debugging and test preservation | Debug and implementation workflows |
| Security, prompt-injection, and secret handling | Security policy and web-search protocol |
| Planning/review/release separation | Role matrix, workflow entry/exit criteria, and approval gates |

## Licensing and copying boundary

The referenced repository reports GPL-3.0 and aggregates material with mixed provenance. We therefore did **not** transplant long prompt passages, proprietary tool schemas, brand-specific instructions, credentials, or provider-specific operational claims into `.agents/`. The files here are an original synthesis of general engineering patterns plus Project Chameleon's own contract rules.

If future work imports verbatim prompt text, it MUST record the exact source revision, preserve applicable license/attribution obligations, and obtain a human legal/licensing decision before distribution. Adaptation does not make source-specific restrictions disappear.
