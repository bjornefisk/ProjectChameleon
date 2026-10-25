# Issue #71 work plan: clean-build dependency provenance

## Scope

Make one release candidate's build inputs traceable and qualify the offline
`linux/amd64` image through a clean native path. Preserve the existing Stage 1
runtime boundary and fail-closed publication behavior.

This work branch implements Issue #71 after the owner authorized the bounded
package-lock strategy in the direct task instruction. Local Darwin arm64
smokes are supplemental and do not establish native qualification.

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

## Accepted lock strategy and qualification status

ADR-013 records the accepted Debian snapshot and exact apt closure, hash-locked
Python runtime/build requirements, and source-bound local renderer wheel. The
implementation is in this branch; the direct task instruction is the owner
approval. The earlier public Issue comment requested approval and is not
misrepresented as granting it.

Local verification has passed repository wiring, the corrected Python 3.11
setup path, a locked amd64 image build, three offline sample successes, and a
malformed-input failure with no output artifacts. The Docker run was
linux/amd64 emulation on Darwin arm64. It is supplemental only.

Native GitHub Actions `linux/amd64` clean-build qualification, SBOM, package
and native-library closure, repeated/clean-cache artifact hashes, and
independent review remain required before closure. Do not claim the lock
candidate is qualified until those results are recorded.

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

- Native amd64 CI and independent repository-maintainer review remain required.
- The package-lock strategy has owner authorization in the direct task instruction and is ratified by ADR-013.
- Do not invent CPU, RAM, time, or scoring limits.
- Do not add model, CP-SAT, OR-Tools, or runtime network dependencies.
- Do not treat a warning-only check or emulated run as release qualification.

## PR lifecycle

Use `Refs #71` while this PR is in progress. Convert to ready only after the
approved lock strategy and qualification evidence exist. Close Issue #71 after
acceptance evidence, then squash-merge into `main`; delete this branch after
merge.
