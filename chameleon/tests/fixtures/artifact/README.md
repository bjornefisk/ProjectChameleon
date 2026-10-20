# Artifact fixtures

The JSON files in this directory are small, deterministic design payloads used
by artifact-gate regression tests. `shape.json` is loaded by the publication,
candidate, and direct validation regressions; those tests deliberately generate
a readable white PNG in a temporary path and assert that the PNG decodes before
the semantic gate rejects its wrong pixels. This keeps invalid artifact bytes
out of the repository while preserving an explicit fixture path.
