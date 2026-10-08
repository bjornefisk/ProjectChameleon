# Role contract template

```yaml
id: chameleon.role.example
version: 1.0
kind: role
capabilities: []
web_search: no
risk: medium
owner: assigned role owner
review: independent reviewer or decision owner
```

# Example role

## Mission

[Observable responsibility and explicit non-goal.]

## Authority and non-goals

[Required authority, owned outputs, prohibited scope.]

## Required inputs

[Task packet, context, evidence, environment.]

## Allowed tools

[Capability IDs, default-deny exceptions, target bounds.]

## Operating loop

[Ordered steps and transitions.]

## Quality gates

[Observable readiness/completion criteria.]

## Failure and stop behavior

[Classify failure, preserve evidence, escalation, rollback.]

## Security

[Data/trust/tool boundary and defensive limits.]

## Evidence and handoff

[Output schema, claim labels, next owner, checks not run.]
```

A new role also requires a dispatch entry, tool-policy review, workflow/checklist coverage, and a repository governance check.
