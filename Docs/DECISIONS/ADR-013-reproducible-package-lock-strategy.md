# ADR-013: Proposed reproducible package-lock strategy

## Status

Proposed — owner approval is required before any dependency or packaging input changes.

## Date / owner / proposer

- Date: 2026-10-23
- Owner: `@bjornefisk`
- Proposer: `@gabegaines24`
- Issue: #71
- Reviewers: repository maintainer review pending; owner approval pending
- Supersedes: None; new proposal
- Recheck: 2026-10-30, or before the first dependency/package change, whichever comes first

## Context

The current Stage 1 image pins the Python 3.11.11 base-image manifest, direct Python requirements, the `cr-renderer` source revision, and packaged assets/fonts. Native `linux/amd64` CI has passed offline sample execution, SBOM generation, repeated hashes, clean-cache hashes, native imports, and library closure.

The remaining reproducibility gap is build-input closure. `chameleon/Dockerfile` names apt packages without exact versions, and pip resolves transitive Python distributions during the build. Direct version pins and a successful clean-cache build do not prove that future builds select identical apt archives and wheels.

This proposal records a reviewable strategy. It is not an accepted dependency decision and does not change the image, requirements, runtime, or public API.

## Proposed decision

Use one release-candidate lock set with these boundaries:

1. Keep the existing immutable Python base-image manifest and qualify the selected `linux/amd64` child digest.
2. Select one timestamped Debian snapshot for the base-image suite and security archive. Replace inherited apt sources with only the recorded snapshot and security sources. Record the snapshot URLs, suite, exact package versions, Release/InRelease signature verification, downloaded `.deb` SHA-256 values, `apt-cache policy` origin/version assertions, and the `dpkg-query` result. For snapshots whose metadata is older than its `Valid-Until` window, set `check-valid-until=no` only on the recorded snapshot source while retaining signature and archive-hash verification.
3. Build a Python 3.11 `linux/amd64` wheelhouse containing every third-party distribution required by the application. Prefer hashed wheels for every dependency and install only from that local wheelhouse with `PIP_CACHE_DIR=/tmp/empty-pip-cache pip install --no-cache-dir --no-index --find-links=<wheelhouse> --require-hashes --only-binary=:all:`. Do not pass the current VCS renderer requirement through pip hash-checking mode.
4. Package the pinned `cr-renderer` revision as an immutable local artifact rather than resolving a VCS or index result during the release build. Record a manifest mapping the upstream commit SHA to the artifact SHA-256 and installed provenance evidence, including `direct_url.json` or its documented equivalent. Prefer a prebuilt verified local wheel and install it with `--no-cache-dir --no-index --find-links=<wheelhouse> --no-deps`. If a source build is unavoidable, lock and preinstall every PEP 517 build requirement from the wheelhouse, build with `--no-build-isolation --no-deps`, hash the generated wheel, and install only that local artifact; never let pip resolve the VCS URL or an unrecorded index result.
5. Make the release build consume only the recorded base image, exclusive snapshot archives, local wheelhouse, renderer artifact, and repository sources. Assert the apt source set before installation and keep runtime `--network none`.
6. Record `pip inspect`/`pip freeze`, `dpkg-query`, native-library `ldd` closure, SBOM digest, packaged asset/font hashes, image digest, sample JSON/PNG/marker hashes, and failure-path evidence.
7. Repeat the build and sample run on native `linux/amd64` with clean caches. Compare the complete recorded input and output hashes. Keep Apple Silicon emulation supplemental.

The proposal does not select package versions or a Debian timestamp. Those values require owner review and source-backed collection on the release candidate.

## Alternatives considered

### Retain direct pins and record observed resolution

Rejected for release closure. Direct pins do not constrain unpinned apt packages or every transitive wheel, so clean-cache builds can resolve different bytes.

### Add a new lock/build tool without changing the current packaging boundary

Deferred. A new tool would add another dependency and workflow decision. The current image uses pip and apt; a lock strategy should first close those paths without expanding solver or runtime scope.

### Use a timestamped Debian snapshot plus a complete hashed wheelhouse

Recommended. Debian documents snapshot archives as historical package states that can be used as apt repositories, and pip documents hash-checking mode as requiring pinned, hashed direct and transitive requirements. This path has higher initial artifact storage and maintenance cost but gives the clearest audit boundary.

## Evidence sources

- **OBSERVED, Debian Project, snapshot.debian.org, retrieved 2026-10-23:** https://snapshot.debian.org/
  - Inspected “Usage” and timestamped archive-source examples. The page documents historical Debian states and apt source entries for those snapshots.
  - The retrieved landing page exposes no immutable page revision or publication date. Scope: apt archive selection and historical package availability. The release candidate must record an exact snapshot timestamp, source-file contents, signature state, and package hashes before acceptance.
- **OBSERVED, Python Packaging Authority, pip secure-install source at tag `26.2.2` (tag object `147fd2284a1f3222683b4176269658a47a72de95`, target commit `b3b696fe2122f2339d782517559bfade2cb6b879`), retrieved 2026-10-23:** https://raw.githubusercontent.com/pypa/pip/b3b696fe2122f2339d782517559bfade2cb6b879/docs/html/topics/secure-installs.md
  - Inspected “Hash-checking Mode,” “Additional restrictions,” “Forcing Hash-checking mode,” and local project installation guidance. pip documents `--require-hashes`, pinned requirements, `--only-binary=:all:`, and `--no-deps` for local project installation.
  - Scope: pip distribution verification. It does not lock Debian packages or authorize a new project build tool.
- **OBSERVED, repository evidence retrieved 2026-10-23 at source revision `31ef5264a3bdbe522388e2d162a95ae0dc64c049`:** `Docs/DEPENDENCY_EVIDENCE.md` at the `### Issue #71 clean-build dependency provenance` and `### Native amd64 CI qualification evidence` sections records the current direct-pin inputs, native CI run `39988562284`, and unresolved package closure. Scope limit: those observations bind the current direct-pin image, not the proposed lock candidate.
- **AUTHORITY REFERENCE (not an evidence classification):** `Docs/PROJECT_CONTRACT.md` §9 and ADR-004 require the pinned offline `linux/amd64` runtime and prohibit unapproved dependency/runtime expansion.

## Consequences

- The release build gains a finite, auditable apt and Python artifact set.
- Wheelhouse storage and rebuild work increase; every supported `linux/amd64` wheel must be retained or regenerated from recorded sources.
- Debian snapshot availability and artifact retention become release-maintenance responsibilities.
- Native amd64, cross-platform parity, official scoring, and organizer resource limits remain separate evidence gates.
- No package, Dockerfile, requirements, schema, runtime, or public API change is authorized by this proposal.

## Security, dependency, and data impact

- Hash-checked artifacts reduce accidental or remote distribution drift, but hashes do not prove that a package is safe or that its license permits redistribution.
- The proposed wheelhouse and apt archive records contain public package artifacts only. Do not store credentials, private indexes, hidden task inputs, or confidential organizer results.
- The build must fail on missing or mismatched hashes rather than resolving an unrecorded alternative.
- Runtime network access remains disabled. Build-time retrieval must be replaced by recorded local inputs before the final offline qualification run.

## Migration and rollback

- Keep the current direct-pin image as the baseline until the owner approves the strategy and a new candidate passes all checks.
- Implement lock inputs in an isolated change. Do not overwrite the current requirements or Dockerfile until the candidate's package and artifact evidence is complete.
- Roll back by reverting the approved lock-input commit and retaining the previous baseline image. A hash mismatch, unavailable snapshot, failed native build, or artifact drift blocks promotion; it does not justify weakening the lock.
- No schema, wire-format, or public API migration is required.

## Affected files and callers

Potential implementation files after approval:

- `chameleon/Dockerfile`
- `chameleon/requirements.txt` or a new checked-in hash-locked requirements artifact
- a checked-in wheelhouse manifest and renderer artifact record
- `.github/workflows/ci.yml`
- `Docs/DEPENDENCY_EVIDENCE.md`, `Docs/STATUS.md`, and a run record

This proposal changes none of those inputs and adds no schema field, runtime dependency, model, solver, or public API.

## Required verification before acceptance

1. Record owner approval and the selected Debian snapshot, suite, exact apt versions, archive hashes, Release/InRelease signature state, the exclusive apt source set, `apt-cache policy` assertions, and the recorded `Valid-Until` handling.
2. Generate the complete Python 3.11 `linux/amd64` wheelhouse. Verify every third-party requirement with pinned hashes and `PIP_CACHE_DIR=/tmp/empty-pip-cache pip install --no-cache-dir --no-index --find-links=<wheelhouse> --require-hashes --only-binary=:all:`. Install the renderer from its verified local wheel with dependencies disabled, or document its separately locked dependencies. If a compatible renderer wheel does not exist, lock and preinstall every PEP 517 build requirement from the wheelhouse, build with `--no-build-isolation --no-deps`, hash the generated wheel, and install only that local artifact. A source-archive hash alone is not closure.
3. Record the immutable renderer artifact manifest mapping the pinned commit SHA, artifact SHA-256, and installed provenance evidence; prove imports from the local artifact.
4. Verify license and notice compatibility for every Debian package, Python distribution, and renderer artifact. Missing license or notice evidence blocks acceptance.
5. Build from clean cache on native `linux/amd64`; capture image digest, SBOM, package closure, native-library closure, and all input hashes.
6. Run all three samples with `--network none`; verify complete JSON/PNG/commit-marker pairs, repeated hashes, and clean-cache hashes.
7. Exercise a failure path and verify that no partial artifact pair remains.
8. Record organizer-controlled limits as unverified unless an authoritative source supplies them.

These checks are not run by this proposal. Existing native CI evidence covers the current direct-pin image, not an approved lock candidate.

## Open external facts

- Owner approval of this strategy and exact lock inputs.
- Availability and retention policy for the selected Debian snapshot and all wheelhouse artifacts.
- Native amd64 qualification for the resulting locked image.
- Cross-platform artifact parity, official scoring, and organizer resource limits.

## Approval gate

`@bjornefisk` must approve the strategy and any exact lock inputs before implementation. Until approval, Issue #71 remains open and the current direct-pin image remains the release-candidate baseline with its documented limitations.
