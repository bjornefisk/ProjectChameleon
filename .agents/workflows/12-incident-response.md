---
id: chameleon.workflow.incident-response
version: 1.0
owner: lead-orchestrator + security-reviewer
entry: suspected secret exposure, unsafe mutation, data loss, compromise, or misleading production artifact
exit: contained incident, evidence-preserving handoff, and follow-up owner
---

# 12 — Incident response

## Purpose

Contain a security, data, integrity, or operational incident without destroying evidence or expanding access.

## Procedure

1. Stop the unsafe action or automation; do not retry blindly.
2. Classify the signal, affected assets, time window, actors/tools, and current exposure.
3. Preserve minimal relevant logs, refs, commands, artifacts, and hashes; redact secrets and personal data.
4. Revoke/rotate credentials through the authorized owner if exposure is plausible; do not copy the secret into the report.
5. Isolate affected branch/artifact/environment when authorized; preserve the last known-good state.
6. Notify project/security/release owners through the approved channel with impact, evidence, and containment.
7. Investigate root cause only within authorization; do not exploit or probe unrelated systems.
8. Record remediation, regression/monitoring evidence, communication, residual risk, and post-incident decision.

## Exit gate

Exposure is contained or explicitly owned, evidence is preserved, affected outputs are identified, credentials/permissions are handled, and corrective action has an owner/date.

## Stop conditions

Live-system access without authorization, continuing exfiltration, uncertain scope, destructive cleanup, or inability to preserve evidence. Escalate immediately.

## Handoff

Use [`../policies/security.md`](../policies/security.md), [`../templates/incident.md`](../templates/incident.md), and [`../checklists/incident.md`](../checklists/incident.md). Do not publish sensitive details in public issues/PRs.
