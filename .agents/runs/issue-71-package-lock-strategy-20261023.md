# Issue #71 package-lock strategy research

**Date:** 2026-10-23
**Issue:** #71
**Branch:** `fix/issue-71-package-lock-strategy`
**Scope:** proposal for apt and transitive Python dependency closure

## Observed sources

- Debian snapshot archive, retrieved 2026-10-23:
  https://snapshot.debian.org/
  - Debian documents timestamped historical archive states that can be used as apt repositories.
- pip secure installs, retrieved 2026-10-23:
  https://pip.pypa.io/en/stable/topics/secure-installs/
  - pip documents `--require-hashes` and requires pinned, hashed direct and transitive requirements in hash-checking mode.

## Proposal

ADR-013 proposes one release-candidate lock set:

- retain the immutable Python base-image manifest and qualify the amd64 child digest;
- select and record one Debian snapshot timestamp, suite, exact apt versions, Release verification, archive hashes, and `dpkg-query` output;
- build a Python 3.11 `linux/amd64` wheelhouse containing every direct and transitive distribution with SHA-256 hashes;
- package the pinned `cr-renderer` revision as an immutable local artifact;
- build from those recorded inputs and keep runtime `--network none`;
- record package closure, SBOM, native-library closure, asset/font hashes, image digest, sample artifact hashes, and failure-path evidence.

## Result

- No dependency, Dockerfile, requirements, or runtime input changed.
- No exact apt version, snapshot timestamp, or wheelhouse was invented.
- Owner approval remains required before implementation.
- Native amd64 CI evidence and offline sample evidence remain separate from full package closure.
- Issue #71 remains open.
