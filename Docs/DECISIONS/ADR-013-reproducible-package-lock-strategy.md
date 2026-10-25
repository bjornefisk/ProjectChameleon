# ADR-013: Reproducible Stage 1 package-lock strategy

## Status

Accepted

## Date / owner / proposer

- Date: 2026-10-25
- Owner: `@bjornefisk`
- Proposer: repository maintainer
- Issue: #71
- Approval authority: the issue owner directly instructed the agent to complete Issue #71, apply required changes, test them, open a PR, and merge it. This is approval in the current task, not a claim that an earlier public Issue comment approved the strategy.
- Review: updated-head native run `40228417003` passed on candidate `a2b8543`; its uploaded SPDX-2.3 artifact was inspected and its SHA-256 matched the workflow digest. Verify the current PR-head required check and repository-maintainer review before merge; neither is superseded by this candidate run.
- Supersedes: the packaging-input detail in ADR-004 that pointed to direct pins in `requirements.txt`. The `linux/amd64`, Python 3.11, CPU-only, and offline-runtime boundaries are unchanged.

## Context

Stage 1 requires a pinned `linux/amd64` image and runtime network isolation. The prior image fixed its Python base image and renderer commit, but apt package selection was unversioned and pip resolved the transitive Python closure during build. A successful clean build of that image did not establish an immutable package closure.

Issue #71 required exact base, apt, Python, renderer, native-library, font, and asset provenance; a reviewed apt/Python lock strategy; hash-locked wheels; native amd64 qualification; SBOM and package closure; all three offline samples; deterministic artifact hashes; and fail-closed failure behavior. Organizer-controlled limits remain unverified and are not package or runtime gates.

The issue owner authorized completion of this bounded packaging work in the direct task instruction recorded above. No public Issue comment is represented as approval.

## Decision

1. Keep the immutable Python index image `python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5`, explicitly build `linux/amd64`, and record its selected child manifest digest. The pinned base image also fixes the Python patch release and bootstrapping tools.
2. Replace inherited apt sources with only the exact Debian Bookworm and Bookworm Security snapshots in `chameleon/apt/sources.list`. Record both InRelease SHA-256 values and signature-verification state in `snapshot-evidence.json`. Lock all 54 newly installed packages and every `.deb` SHA-256. Install only the four exact runtime roots with `--no-install-recommends`, compare the complete added `dpkg-query` closure to `packages.lock`, and require each package's Debian copyright notice. `check-valid-until=no` applies only to the immutable security snapshot; apt signature verification and downloaded archive hash checks remain enabled.
3. Keep editable Python constraints in `requirements.in` and the renderer's PEP 517 build constraints in `renderer-build.in`. Their checked-in `.lock` files pin every distribution and carry hashes. The runtime closure is derived from the pinned renderer's `uv.lock`, with the project's pinned JSON Schema validator additions. The renderer build lock pins Hatchling and its full build closure; its `packaging` version is aligned with the runtime lock so one generated wheelhouse can serve both.
4. Generate, do not commit, the `linux/amd64` `.wheelhouse/` with `scripts/prepare_dependency_inputs.py`. Use the pinned Python base image to download only binary distributions with `--require-hashes --only-binary=:all:`. The helper verifies the renderer source archive SHA-256, installs locked build requirements from the wheelhouse, builds the renderer wheel with `--no-build-isolation --no-deps`, enforces the artifact manifest's wheel hash, and records every wheel filename, size, and SHA-256. Existing generated wheelhouses are reused only after input and file-hash verification; stale or altered contents fail closed.
5. Bind the renderer source repository and commit to the exact source archive and wheel in `renderer-artifact.json`. Build the pure-Python wheel with the locked backend and `SOURCE_DATE_EPOCH`; the two independently observed builds produced the same SHA-256. Install only that local wheel with `--no-index --no-deps`, then verify PEP 610 `direct_url.json`'s archive hash against the manifest. Do not install from VCS or resolve a renderer index release.
6. The Docker build consumes the pinned base image, the exclusive signed apt snapshot, the committed lock files, and the generated verified wheelhouse. Python installation uses `--no-index`, `--require-hashes`, `--only-binary=:all:`, and an empty pip cache. The image records its package locks, apt closure, `pip inspect`, and `pip freeze` under `/app/provenance/`. Runtime execution remains `--network none`; no model, solver, schema, or public API scope changes.
7. Preserve each third-party license and notice in its package's installed distribution metadata/files or Debian `/usr/share/doc/<package>/copyright`. Verify the renderer's Apache-2.0 license, every wheel's license metadata/notice file, and the apt package notices. The SBOM and exact package closure are separate from this license review; hashes alone do not establish license compatibility.
8. Qualify the exact candidate on native x86_64 GitHub Actions with a clean-cache amd64 build, a non-empty SPDX JSON SBOM uploaded as a workflow artifact with its SHA-256 recorded, package/native-library closure, offline samples and failure path, repeated/clean-cache artifact hashes, and provenance. Apple Silicon emulation is supplemental. Do not infer organizer limits or release qualification from these build checks.

## Alternatives considered

### Retain direct pins and record observed resolution

Rejected. Direct pins do not constrain unpinned apt packages or every transitive wheel, so future builds can select different dependency bytes.

### Commit all downloaded wheels

Rejected for the product repository. Wheels are reproducibly selected from the complete hash locks and generated in an ignored local wheelhouse; committing the large platform-specific artifacts would duplicate the lock and source evidence. Availability of public archives remains a maintenance risk, while hash mismatches fail closed.

### Keep resolving the renderer from VCS or PyPI at image build time

Rejected. The upstream revision has no usable pinned PyPI artifact; pip VCS resolution is not a complete hash-locked wheel closure. The source archive and locally built wheel are both fixed by SHA-256 and source commit.

### Keep live apt/PyPI resolution in Dockerfile

Rejected. A clean cache does not make remote package selection immutable. Apt now uses a timestamped signed snapshot and package archive hashes; Python installation consumes only the local wheelhouse.

## Evidence sources

- **Authority:** `Docs/PROJECT_CONTRACT.md` §9 and ADR-004 preserve the pinned `linux/amd64` runtime and no-network execution boundary.
- **Owner approval:** direct task instruction from `@bjornefisk`, 2026-10-25. The earlier public Issue comment `6373327459` requested strategy approval but did not approve it.
- **Debian Project, retrieved 2026-10-25:** [snapshot.debian.org](https://snapshot.debian.org/) documents historical archive sources. The selected source URLs, InRelease hashes, keyring version, package versions, archive hashes, and Valid-Until treatment are recorded in `chameleon/apt/snapshot-evidence.json` and the adjacent lock files.
- **Python Packaging Authority, pip secure-install documentation:** [Hash-checking mode](https://pip.pypa.io/en/stable/topics/secure-installs/) documents pinned, hashed requirements and `--require-hashes`; the implementation additionally requires binary wheels and prohibits index access during image install.
- **Pinned renderer source:** upstream commit [`a17e1fb9a732959dd6c21ae168d5ee09d74bd64f`](https://github.com/CyberAgentAILab/cr-renderer/commit/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f), verified source archive SHA-256 and locally built wheel SHA-256 are recorded in `chameleon/renderer-artifact.json`.
- **Candidate package evidence:** `Docs/DEPENDENCY_EVIDENCE.md`, `.agents/runs/`, the generated wheelhouse manifest, image SBOM, and the candidate CI run record the input/output evidence. The prior native run for the direct-pin image is historical only.

## Consequences

- Each promoted image has a finite, auditable apt and Python artifact closure.
- Build preparation still needs public network access to retrieve the exact Debian snapshot, hash-locked PyPI wheels, and renderer source archive. A missing or changed public artifact blocks preparation; it does not select a substitute.
- The generated wheelhouse is ignored and regenerated from its committed hashes. Public snapshot/archive retention is not guaranteed by this decision.
- Every dependency change requires lock regeneration, source/license review, updated provenance, and native amd64 CI. A source or package hash mismatch blocks promotion.
- Cross-platform parity, organizer-held-out scoring, official limits, and release qualification remain separate evidence gates.

## Security, dependency, and data impact

- Hash-checked artifacts reduce accidental or remote distribution drift; hashes do not prove that code is safe or that a license permits redistribution.
- The wheelhouse contains public package artifacts only. Do not store credentials, private indexes, hidden task inputs, or confidential organizer results.
- Missing package archives, invalid apt signatures, mismatched hashes, unexpected package closure, missing notices, or failed offline qualification block the candidate.
- The runtime has no network access. The image installs Python only from verified local artifacts and does not retain the wheelhouse.

## Migration and rollback

- Replace the old VCS/direct-pin install with the source archive manifest, checked-in lock files, wheelhouse preparer, and local-artifact image install. Migrate all developer, Docker, CI, review-tool, and documentation callers; do not keep a `requirements.txt` compatibility path.
- Roll back by reverting the lock-input and Dockerfile change as one unit. Retain the prior base image only as historical evidence; do not call it a qualified lock candidate.
- No schema, wire-format, solver, runtime network, or public API migration is required.

## Affected files and callers

- `chameleon/Dockerfile`
- `chameleon/requirements.in`, `chameleon/requirements.lock`
- `chameleon/renderer-build.in`, `chameleon/renderer-build.lock`, `chameleon/renderer-artifact.json`
- `chameleon/apt/sources.list`, `chameleon/apt/packages.lock`, `chameleon/apt/packages.sha256`, `chameleon/apt/snapshot-evidence.json`
- `scripts/prepare_dependency_inputs.py`, `Makefile`, `chameleon/.gitignore`
- `.github/workflows/ci.yml`, dependency provenance tests, and the PR review dependency trigger
- `Docs/PROJECT_CONTRACT.md` §9, ADR-004, `Docs/DEPENDENCY_EVIDENCE.md`, `Docs/STATUS.md`, `tasks/`, and `.agents/runs/`

## Required verification before Issue #71 closure

1. Verify source and lock hashes, apt source exclusivity/signatures, exact apt package closure/archive hashes, and license notices.
2. Prepare the complete Python 3.11 `linux/amd64` wheelhouse from hashes; verify all locked runtime/build wheels and the source-bound renderer wheel.
3. Build from clean cache on native `linux/amd64`; capture image digest, SBOM, `dpkg-query`, `pip inspect`/`pip freeze`, and native-library closure.
4. Run all three samples with `--network none`; verify exact JSON/PNG/commit-marker pairs, repeated hashes, and clean-cache hashes.
5. Exercise malformed input and verify nonzero status with an empty output directory; keep the permanent runner failure-cleanup tests.
6. Record each command/result in the candidate run record. Do not use the historical direct-pin CI run or arm64-host emulation as lock-candidate evidence.
7. Keep organizer-controlled limits, official scoring, cross-platform parity, and release qualification explicitly unverified unless authoritative evidence is obtained.

## Open external facts

- Long-term retention/availability guarantees for the selected Debian snapshot, PyPI wheels, and the GitHub source archive are not specified by this ADR. Hash mismatches or missing artifacts stop the build.
- Cross-platform parity, organizer-held-out scoring, official thresholds, resource limits, and final Adobe deployment topology remain unverified.
