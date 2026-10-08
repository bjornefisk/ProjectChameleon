# Dependency and external-source policy

## Source-driven change

Inspect the authoritative package/source, exact revision, adapter, and existing evidence before relying on external behavior. Record why the dependency is needed, version/revision, license, platform/runtime impact, transitive risk, offline behavior, and rollback.

## Pinning

Do not use unpinned latest behavior as a contract. A plan must name the immutable version/commit or label the fact `UNVERIFIED_EXTERNAL_FACT`. Update `Docs/DEPENDENCY_EVIDENCE.md` or the applicable authority when a dependency decision is accepted.

## Network boundary

Agent web research is a development-time capability. Project Chameleon Stage 1 runtime remains offline, including the documented Docker smoke path. Never add runtime downloads, model fetching, telemetry, or network fallback to make a check pass.

## Qualification

Verify package/source resolution, adapter behavior, platform/native libraries, license/notice requirements, reproducibility, and failure when unavailable. A successful local install is not evidence of native-amd64 or offline qualification.

## Stop conditions

Missing provenance/license, incompatible contract, unverified platform guarantee, dependency only available through forbidden network access, or a request to silently change versions. Escalate through change control and security review.
