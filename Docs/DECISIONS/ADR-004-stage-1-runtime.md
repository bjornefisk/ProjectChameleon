# ADR-004: Define the Stage 1 runtime and hardware target

## Status

Accepted

## Date

2026-10-06

## Context

The challenge requires offline Stage 1 execution and a `linux/amd64` container. The starter image uses a moving `python:3.11-slim` tag, live Git/PyPI resolution, and unversioned apt packages. Development commonly occurs on Apple Silicon, while the rules mention an Apple M5 Pro reference machine without exact resource limits.

## Decision

- The Stage 1 artifact is a single-platform `linux/amd64` OCI image.
- The image uses Python 3.11 with an immutable explicit base-image digest and the direct compatibility pins in `chameleon/requirements.txt`.
- Build-time network access may fetch the pinned source and packages. Runtime network access is disabled with `--network none`; fonts, assets, renderer code, and dependencies are already in the image.
- Apple Silicon development must build the amd64 target with Docker Buildx or qualify on native amd64. An arm64-only build is not conformance evidence.
- No model runtime or OR-Tools dependency is part of the ratified baseline. A later model or solver requires its own immutable artifact/dependency and resource decision.
- The exact M5 Pro CPU/RAM/disk/GPU budget, model allowlist, and model-size cap remain organizer-controlled TBD facts. This ADR does not invent them, and Stage 1 has no hard latency disqualifier in the supplied rules.

The initial base image is `python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5`, the Docker Hub OCI index observed during ratification. The selected linux/amd64 child digest and apt package versions still require build qualification; see `STATUS.md`.

## Alternatives considered

### Allow the floating `python:3.11-slim` and Git default branch

Rejected. Renderer behavior, native wheels, and OS layers could change between clean builds.

### Make the image arm64 because development uses Apple Silicon

Rejected. It conflicts with the published Stage 1 scoring target.

### Claim a complete hardware budget from “Apple M5 Pro”

Rejected. The repository explicitly marks the CPU/RAM/disk/GPU details TBD.

### Add CP-SAT now because the architecture mentions it

Rejected. OR-Tools is not present, and solver choice is an implementation decision after contract ratification.

## Consequences

- Docker Buildx/QEMU may make Apple Silicon local builds slower; native amd64 CI remains required.
- A pinned direct dependency baseline improves reproducibility but is not a complete hash-locked wheelhouse until the packaging follow-up is done.
- Resource-sensitive model work is blocked until organizer limits are published.
- Runtime network isolation is a deployment requirement, not something the image alone can guarantee.

## Affected files/schema fields

- `chameleon/Dockerfile`
- `chameleon/requirements.txt`
- `Docs/HERMETIC_RUNTIME_ARCHITECTURE.md`
- `chameleon/brand_kit/` fonts/assets and any future model artifacts

## Required validation tests

- Build with `docker buildx build --platform linux/amd64` and inspect the image architecture and Python patch version.
- Run with `--network none`, empty caches, and only mounted input/output; verify the samples render without network access.
- Record `pip freeze`, VCS direct URL, native-library imports, font loading, and a representative PNG hash in a clean amd64 build.
- Repeat on native amd64 and Apple Silicon Buildx output; compare dependency wheels and rendered fixtures.
