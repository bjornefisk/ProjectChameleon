# Issue #71 work plan: clean-build dependency provenance

## Scope

Make one release candidate's build inputs traceable and qualify the offline
`linux/amd64` image through a clean native path. Preserve the existing Stage 1
runtime boundary and fail-closed publication behavior.

This draft PR establishes the issue-specific work branch. It does not claim
native qualification from arm64-host emulation.

## Ordered slices

1. Freeze the candidate commit and inventory base image, apt packages, Python
   dependencies, renderer revision, native libraries, fonts, and assets.
2. Decide the reviewed package-lock strategy for apt and transitive Python
   dependencies, including whether a complete hash-locked wheelhouse is
   required.
3. Record any durable strategy through the required ADR and dependency evidence
   path before changing pins or packaging.
4. Implement only approved dependency changes; keep network disabled at runtime
   and keep model/solver scope unchanged.
5. Build with clean cache on native `linux/amd64`.
6. Capture image digest, SBOM, package closure, input hashes, platform, Python,
   renderer, and exit status.
7. Run all samples with `--network none`, verify complete JSON/PNG/marker pairs,
   test failure-path cleanup, repeat artifacts, and compare clean-cache hashes.
8. Record residual organizer-controlled limits as unverified.

## Acceptance criteria

- Base image, apt, Python, renderer, native-library, font, and asset inputs are
  inventoried for the candidate.
- Lock strategy is reviewed before dependency changes land.
- Native amd64 clean build and offline runtime pass all three samples.
- Repeated and clean-cache artifacts are deterministic.
- Failed tasks publish no partial artifact pairs.
- Arm64-host emulation is labeled supplemental, not native qualification.

## Verification

- `make verify`
- `make test` in the required Python 3.11 environment.
- Exact Buildx, SBOM, native runtime, clean-cache, and repeated-hash workflow in
  `.github/workflows/ci.yml`.
- Review `.agents/runs/`, `Docs/STATUS.md`, and
  `Docs/DEPENDENCY_EVIDENCE.md` before closure.

## Dependencies and non-goals

- Native amd64 CI/build capacity and an owner-approved lock strategy are
  required.
- Do not invent CPU, RAM, time, or scoring limits.
- Do not add model, CP-SAT, OR-Tools, or runtime network dependencies.
- Do not treat a warning-only check or emulated run as release qualification.

## PR lifecycle

Use `Refs #71` while this PR is in progress. Convert to ready only after the
approved lock strategy and qualification evidence exist. Close Issue #71 after
acceptance evidence, then squash-merge into `main`; delete this branch after
merge.
