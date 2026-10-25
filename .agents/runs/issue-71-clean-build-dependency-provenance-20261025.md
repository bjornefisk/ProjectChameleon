# Run record: Issue #71 clean-build dependency provenance

```text
run_id: issue-71-clean-build-dependency-provenance-20261025
owner/role: Lead orchestrator / implementation owner
workflow/gate: Issue #71 dependency provenance and native qualification
started/updated: 2026-10-25 / pending native CI and final review evidence
branch/ref: fix/issue-71-clean-build-provenance
source revision: main 84d8e3e00bc457dfb3714bf368700da2ff3620d; implementation is an uncommitted worktree diff at initial evidence capture
worktree state: implementation and tests present; generated wheelhouse ignored; no candidate CI run or PR yet

Goal/acceptance: close every Issue #71 build-input provenance gap, demonstrate an offline success artifact pair and fail-closed no-pair behavior, and qualify the exact candidate on native x86_64 GitHub Actions before merge.

Authority and ADR impact: PROJECT_CONTRACT.md §9; Accepted ADR-002, ADR-004, and ADR-013; Issue #71. The issue owner authorized implementation and merge in the direct task instruction dated 2026-10-25. Issue comment 6373327459 requested approval and is not approval evidence. No schema, renderer API, solver, model, or runtime-network scope expansion.

Environment/platform/versions/network mode: Darwin 27 arm64 host; Python 3.11.14 local venv; Docker Buildx local linux/amd64 emulation; pinned container base Python 3.11.11. Build preparation accessed pinned public package/source inputs; all local runtime smoke executions used --network none. Native x86_64 CI remains unavailable locally.

Inputs/fixtures/seeds: repository sample Level 1/2/3 inputs; one malformed JSON failure input; pinned Debian snapshots, hash locks, and cr-renderer source archive. No hidden evaluation data.

Out of scope: organizer-held-out scoring, cross-platform hash parity, production-font authorization, unverified organizer budgets, model/CP-SAT/solver changes, and release qualification.
```

## Run flow

1. Intake and comparison of Issue #71 against the project contract and accepted decisions.
2. Implement accepted source-bound Debian/Python/renderer locks, offline installation, build provenance, CI qualification, regression tests, and documentation.
3. Run repository wiring and complete Python test suite.
4. Build and smoke the exact container locally under arm64-host amd64 emulation; exercise success and failure publication paths.
5. Record local evidence as supplemental only; independent implementation and security reviews found no actionable findings. Native GitHub qualification and repository-maintainer review remain gates.

## Commands and observed results

| Check | Exact command | Result | Evidence/artifact |
|---|---|---|---|
| Prepare locked inputs | `make prepare-dependencies PYTHON_BOOTSTRAP=python3.11` | `PASS` (exit `0`) | Existing 46-wheel manifest verified against current lock inputs and wheel hashes. |
| Create local environment | `make setup VENV_DIR=/tmp/chameleon-issue71-setup-fixed.JxX4Ms/venv PYTHON_BOOTSTRAP=python3.11` | `PASS` (exit `0`) | Python `3.11.14`; Pillow `11.1.0`, Skia `132.0b11`, and local `cr-renderer 0.1.0` imported from this venv. |
| Repository wiring | `make verify PYTHON_BOOTSTRAP=python3.11` | `PASS` (exit `0`) | Font provenance manifest and repository governance/wiring passed after final evidence edits. |
| Full test suite | `make test PYTHON=/tmp/chameleon-issue71-setup-fixed.JxX4Ms/venv/bin/python` | `PASS` (exit `0`) | 280 repository tests + 48 review-capsule + 3 runtime qualification + 1 dependency-preparation regression + 3 font-provenance = 335 tests. |
| Build candidate image | `docker buildx build --platform linux/amd64 --load -t chameleon-issue71-candidate chameleon/` | `PASS` (exit `0`) | Loaded image ID `sha256:d266651ef2e013c0b46bea441624469fe3cd05640cc900895211b61c8648b263`, size `352840969` bytes. Docker emitted existing non-blocking `FromPlatformFlagConstDisallowed` warning. |
| Local offline samples | Ad hoc Docker invocation with isolated input/output mounts; exact shell argument string was not retained. | `PASS` (exit `0`, observed) | Level 1/2/3 returned `SUCCESS`; each produced JSON, PNG, and commit marker. Nine hashes are recorded in `Docs/DEPENDENCY_EVIDENCE.md`. This was local arm64-host emulation only. |
| Local malformed-input path | Ad hoc Docker invocation with isolated malformed input/output mounts; exact shell argument string was not retained. | `PASS` (container exit `1`, observed) | Status `MALFORMED_INPUT`; output directory remained empty. Local supplemental evidence only. |
| Independent renderer rebuild | Independent offline `linux/amd64` renderer rebuild using the generated wheelhouse; exact shell argument string was not retained. | `PASS` (observed) | Reproduced `cr_renderer-0.1.0-py3-none-any.whl`, SHA-256 `92b4005c5777d305151321760cfb32e0c8e91a7041ac74fabe630bcc2e06fda9`, size `15950` bytes. |
| Native x86_64 workflow | `.github/workflows/ci.yml`, job `Verify and test`, current PR head | `PENDING` | Required for final qualification: clean-cache amd64 image, SPDX SBOM, package/native closure, all three offline samples, no-pair failure behavior, repeat/clean-cache hashes, and runtime provenance. |
| Independent implementation/security review | Read-only `reviewer` and `security-reviewer` assessment of the candidate diff | `PASS` (no actionable findings) | Contract, acceptance, maintainability, lock/build, CI, trust-boundary, secret/data scopes reviewed; neither agent ran tests or native CI. |
| Whitespace check | `git diff --check` | `PASS` (exit `0`, no output) | No whitespace errors in the worktree patch before commit. |

## Artifacts

- Runtime lock: `chameleon/requirements.lock`, SHA-256 `0386cc02d31ef271ed3ae68d8fc544727a273c8bf9dcb734dc309b87b3ac5b5f`.
- Renderer build lock: `chameleon/renderer-build.lock`, SHA-256 `e4b17a17cd56763c0a8c5491cebd1136aa4dbb1645861b2141443f28df0ff6cf`.
- Renderer source: signed upstream commit `a17e1fb9a732959dd6c21ae168d5ee09d74bd64f`; source archive SHA-256 `18e8bdf0c22d43516829c4a7028b4eb5953f8dc2359ad3fd50054384a2b6ef71`.
- Renderer wheel: `cr_renderer-0.1.0-py3-none-any.whl`, SHA-256 `92b4005c5777d305151321760cfb32e0c8e91a7041ac74fabe630bcc2e06fda9`.
- Generated, ignored wheelhouse: 46 wheels; manifest SHA-256 `5cf515d60e773784b601d71de099e29943ab9e4e513b064a29824103179f3728`.
- Debian snapshot/package evidence: `chameleon/apt/sources.list`, `packages.lock`, `packages.sha256`, and `snapshot-evidence.json`; four exact apt roots and a 54-package added closure. Local image audit found copyright notice files for all 159 installed packages; wheelhouse review found license/notice files for all 46 wheels. This is not legal advice or a license-compatibility determination.
- Local sample JSON/PNG/marker hashes and packaged asset/font SHA-256 values: `Docs/DEPENDENCY_EVIDENCE.md`.
- Published artifacts: none committed; all runtime outputs were temporary/local.

## Warnings and interpretation

- **OBSERVED:** The new regression test covers interpreter symlink preservation. An initial setup attempt exposed that resolving the requested venv Python symlink redirected package installation to the host user site; the helper was fixed to preserve the supplied interpreter path, and the full 335-test suite passed afterward.
- **OBSERVED:** Local emulation build and smoke results do not establish native-amd64 qualification.
- **OBSERVED:** `make verify` and the full test suite passed; tests are not a substitute for native Docker qualification.
- **INFERRED:** Snapshot signatures plus per-archive hashes and complete hash-locked local Python wheels constrain dependency resolution more tightly than the former direct-pin/build-time resolution.
- **UNVERIFIED_EXTERNAL_FACT:** Organizer CPU/RAM/GPU/disk limits, official scoring thresholds, model allowlist, production-font authorization, Adobe deployment topology, and cross-platform hash parity remain unverified; do not add runtime gates or claim release qualification from local measurements.

## Failures and unrun checks

- Failure classification: initial local setup revealed a real venv-symlink bug; fixed and covered by regression test. No final verification command failed.
- Checks not run: native x86_64 GitHub Actions candidate run, SBOM capture for this candidate, final PR-head workflow, and repository-maintainer PR review. These are mandatory before merge.
- Environment or platform limitation: local host is Darwin arm64; Buildx uses amd64 emulation. This does not prove native Linux/amd64 behavior.

## Security and data notes

- Secrets or personal data: no credential values are recorded in this run record or used as dependency inputs.
- Untrusted inputs or external content: pinned package/source inputs were hash/signature verified; sample designs are repository fixtures.
- Network boundary: dependency preparation/build requires network access to retrieve pinned sources/wheels/debs; the container runtime checks use `--network none`.

## Decision and handoff

- Decision: implementation is locally verified and independent agent reviews found no actionable findings, but it is not ready for issue closure or merge until native x86_64 CI, repository-maintainer review, and final-head CI pass.
- Rollback/migration: revert the Issue #71 PR; old `requirements.txt` is removed as part of the clean cutover to reviewed lock inputs.
- Next owner: PR maintainer/reviewer and native GitHub Actions runner.
- Next concrete action: run `git diff --check`, commit, and open a draft PR; record native run and repository-maintainer review evidence here before marking the PR ready.
