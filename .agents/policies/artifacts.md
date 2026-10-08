# Artifact and output policy

## Provenance

Every durable artifact identifies task/run, source revision, generator/tool version, inputs, environment, and validation state when those facts matter. Generated files are evidence only when their provenance and result are inspectable.

## Failure behavior

Do not publish stale, partial, placeholder, hidden, zero-size, opacity-zero, shed, or source-replaced output to disguise invalid behavior. On hard-validation failure, fail closed and preserve a typed failure/infeasibility record without misleading output files.

## Repository hygiene

Keep throwaway experiments outside tracked product paths or remove them after evidence is captured. Do not commit caches, credentials, build output, screenshots, downloaded dependencies, or generated artifacts prohibited by repository governance.

## Retention and redaction

Retain the minimum artifact needed to reproduce or review the decision. Redact secrets and personal data. Reference large artifacts by stable path/hash rather than copying them into prompts or tickets.

## Review gate

Before handoff/release, inspect artifact path, format, source identity, content, asset references, validation status, and cleanup/rollback. A warning-only check or non-empty file is not proof of correctness.
