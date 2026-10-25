# Run record: Issue #71 clean-build dependency provenance

```text
run_id: issue-71-clean-build-dependency-provenance-20261025
owner/role: Lead orchestrator / implementation owner
workflow/gate: Issue #71 dependency provenance and native qualification
started/updated: 2026-10-25 / native run `40227253405` passed without retaining its SBOM; follow-up `40228417003` and PR-head run `40229964417` passed `Verify and test` and their SPDX artifacts were verified; the current `ubuntu-24.04` runner pin still needs a passing check, and maintainer review is pending

branch/ref: `fix/issue-71-clean-build-provenance` / PR [#80](https://github.com/bjornefisk/ProjectChameleon/pull/80) (opened as draft)
source revision: latest passed candidate `b004f609c70440a510ceae645b8ff5de66afb071`; earlier candidates `a2b8543f78bd2504b8d1051621972fb7220e1bce` and `84ed3b4fac95efd208de87383fdc9009e1a48cf8`; based on main `84d8e3e00bc457dfb3714bf368700da2ff3620d`
worktree state: `b004f609c70440a510ceae645b8ff5de66afb071` is pushed and passed run `40229964417`; the workflow's `ubuntu-24.04` pin is a local uncommitted change; PR #80 is draft and maintainer review was requested from `@gabegaines24`.

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
| Repository wiring | `make verify PYTHON_BOOTSTRAP=python3.11` | `PASS` (exit `0`) | Passed on the follow-up worktree after enabling SBOM upload and recording initial native results. |
| Required software preflight | `make preflight PYTHON_BOOTSTRAP=python3.11` | `PASS` (exit `0`) | Nested engine was present; repository governance and implementation wiring passed. |
| Full test suite | `make test PYTHON=/tmp/chameleon-issue71-setup-fixed.JxX4Ms/venv/bin/python` | `PASS` (exit `0`) | 280 repository tests + 48 review-capsule + 3 runtime qualification + 1 dependency-preparation regression + 3 font-provenance = 335 tests. |
| Build candidate image | `docker buildx build --platform linux/amd64 --load -t chameleon-issue71-candidate chameleon/` | `PASS` (exit `0`) | Loaded image ID `sha256:d266651ef2e013c0b46bea441624469fe3cd05640cc900895211b61c8648b263`, size `352840969` bytes. Docker emitted existing non-blocking `FromPlatformFlagConstDisallowed` warning. |
| Local offline samples | Ad hoc Docker invocation with isolated input/output mounts; exact shell argument string was not retained. | `PASS` (exit `0`, observed) | Level 1/2/3 returned `SUCCESS`; each produced JSON, PNG, and commit marker. Nine hashes are recorded in `Docs/DEPENDENCY_EVIDENCE.md`. This was local arm64-host emulation only. |
| Local malformed-input path | Ad hoc Docker invocation with isolated malformed input/output mounts; exact shell argument string was not retained. | `PASS` (container exit `1`, observed) | Status `MALFORMED_INPUT`; output directory remained empty. Local supplemental evidence only. |
| Independent renderer rebuild | Independent offline `linux/amd64` renderer rebuild using the generated wheelhouse; exact shell argument string was not retained. | `PASS` (observed) | Reproduced `cr_renderer-0.1.0-py3-none-any.whl`, SHA-256 `92b4005c5777d305151321760cfb32e0c8e91a7041ac74fabe630bcc2e06fda9`, size `15950` bytes. |
| Native x86_64 qualification, initial candidate | GitHub Actions run [40227253405](https://github.com/bjornefisk/ProjectChameleon/actions/runs/40227253405), job `Verify and test`; merge ref `2d1bfa45830de305560168875ca0c733615fd43d`; candidate head `84ed3b4fac95efd208de87383fdc9009e1a48cf8` | `PASS` (exit `0`) | Native run generated and hashed the SPDX SBOM but the workflow explicitly disabled artifact upload; follow-up run `40228417003` qualified the updated head and retained a verified SPDX artifact. See the updated run evidence below. |
| Native x86_64 qualification, SBOM-retention follow-up | GitHub Actions run [40228417003](https://github.com/bjornefisk/ProjectChameleon/actions/runs/40228417003), job `Verify and test`, candidate head `a2b8543f78bd2504b8d1051621972fb7220e1bce`; merge ref `27eee971346a0b5c6733053b00d91564d1d4820b` | `PASS` (exit `0`) | Native Ubuntu 24.04.5 x86_64 job passed. The workflow SBOM artifact `chameleon-stage1-sbom.spdx.json` (`12611997130`) downloaded and parsed as SPDX-2.3, `chameleon-stage1`, 220 packages, 4,861 relationships, 3,614,257 bytes; SHA-256 `28eb3be04d8bdf5233595e8b752c94f6ea4392ea43aff598503c83efa8981268`, matching the job digest. |
| Native x86_64 qualification, PR-head evidence | GitHub Actions run [40229964417](https://github.com/bjornefisk/ProjectChameleon/actions/runs/40229964417), job `Verify and test`, candidate head `b004f609c70440a510ceae645b8ff5de66afb071` | `PASS` (exit `0`) | Native Ubuntu 24.04.5 x86_64 run passed. The SBOM artifact `chameleon-stage1-sbom.spdx.json` (`12612674286`) parsed as SPDX-2.3, `chameleon-stage1`, 220 packages, 4,861 relationships, 3,614,257 bytes; SHA-256 `75f9def29db2071372d1a7e2ea92fbadea9e1b99bfab073eded669341e796da1`, matching the workflow log. The current runner-label pin postdates this run. |

| Independent implementation/security review | Read-only `reviewer` and `security-reviewer` assessment of the candidate diff | `PASS` (no actionable findings) | Contract, acceptance, maintainability, lock/build, CI, trust-boundary, secret/data scopes reviewed; neither agent ran tests or native CI. |
| Repository maintainer review | PR #80 review request to `@gabegaines24` | `PENDING` | Requested on the draft PR; no human review recorded yet. |
| Repository wiring/whitespace | `git diff --check && make verify PYTHON_BOOTSTRAP=python3.11` | `PASS` (exit `0`) | `git diff --check` emitted no errors; repository verification reported `Font provenance manifest verified` and `Repository governance and implementation wiring are consistent.` |

## Initial native x86_64 candidate

GitHub Actions run [40227253405](https://github.com/bjornefisk/ProjectChameleon/actions/runs/40227253405) passed job `Verify and test` (exit `0`) on PR head `84ed3b4fac95efd208de87383fdc9009e1a48cf8`, merge ref `2d1bfa45830de305560168875ca0c733615fd43d`. The runner was Ubuntu 24.04 `x86_64`; the container reported Linux, Python `3.11.11`, and `x86_64`.

- Native image: `linux/amd64`, ID `sha256:1355e46ee49ab006fdc792669f083fc68be16bfa35d3af4e674d5cf52494e318`; observed image size `848681354` bytes.
- Clean-cache `linux/amd64` Buildx rebuild passed. The SPDX JSON SBOM passed the non-empty check and had SHA-256 `f13b77debbeec44ff4c58b4100586f685f0c10c5b63aa32cd0399545273c36b3`; the initial workflow disabled artifact upload, so the file was not retained. The follow-up enables workflow-artifact upload and requires a new native run.
- The workflow printed the full installed apt and Python distribution closures. Provenance SHA-256 values: apt snapshot evidence `623c742a22fd9ab591babb3243bd869f39f9fd09f0a8485139863fdcbff6aac1`; apt lock `1c03026a0dcda31a13de1c999060fbc95609a9ce1cae98abb49091bbd6229438`; `.deb` hashes `01e538143bd5110b845e72f00fcb2c0cee05237c0929d0d10917155773e2ade9`; `dpkg-query` closure `db8ccd833d5bd707b3e919e61846aba01f0e72f4e2f0bcca4c05d131e24e5e40`; pip inspection `7d903f5fab12474124095af65bc0e2bc6dece115c3312740649b6f48096e91ae`; pip freeze `2d19f7f7d0a8d3d25cc822d72d3fd92825b57f57e1daefdfd51e1addf52db826`. The Python lock, renderer-build lock, renderer artifact manifest, and wheelhouse manifest hashes matched the checked-in/generated hashes recorded above.
- All three offline samples returned `SUCCESS` and published complete JSON/PNG/commit-marker outputs. The nine native output hashes matched the values in the sample table in `Docs/DEPENDENCY_EVIDENCE.md`. A malformed input returned `MALFORMED_INPUT` with exit `1` and an empty output directory. Repeated-run and clean-cache image artifact hashes matched; offline renderer imports and Skia/Pillow `ldd` closure passed without `not found` entries.
- Native runtime observation: exit `0`; wall time `17.141200913` seconds; user CPU `16.69382` seconds; system CPU `0.45194` seconds; maximum RSS `295776 KiB`; peak `3` procfs threads; `2` available CPUs. These are runner observations, not organizer ceilings.
- Logs included Fontconfig configuration, warning-only off-canvas self-check, and missing-asset renderer warnings. They are not contract-validation evidence.

## Updated-head native x86_64 qualification

GitHub Actions run [40228417003](https://github.com/bjornefisk/ProjectChameleon/actions/runs/40228417003) passed `Verify and test` (exit `0`) on candidate `a2b8543f78bd2504b8d1051621972fb7220e1bce`, merge ref `27eee971346a0b5c6733053b00d91564d1d4820b`. The runner was Ubuntu 24.04.5 `x86_64`; the container reported Linux, Python `3.11.11`, and `x86_64`.

- Native image: `linux/amd64`, ID `sha256:de27cd36d36371c5fc6b571c58849ad068f8abb36bee738ff65524a6a571bfed`; observed size `848681354` bytes.
- Clean-cache `linux/amd64` Buildx rebuild and repeated-runtime plus clean-cache sample artifact comparisons passed. All three offline samples returned `SUCCESS`; the malformed-input path returned `MALFORMED_INPUT`, exit `1`, and left the output directory empty. Native renderer imports and Skia/Pillow `ldd` closure passed without `not found` entries.
- Test stages passed: 280 repository tests, 48 review-capsule tests, 3 runtime-qualification tests, 1 dependency-preparation regression, 3 font-provenance tests, and the separate 1-test native renderer-golden qualification.
- The uploaded workflow artifact `chameleon-stage1-sbom.spdx.json` (artifact ID `12611997130`) is valid SPDX-2.3 for `chameleon-stage1`, with 220 packages, 4,861 relationships, and 3,614,257 extracted bytes. Its SHA-256 is `28eb3be04d8bdf5233595e8b752c94f6ea4392ea43aff598503c83efa8981268`, identical to the workflow's logged digest.
- The workflow printed the same apt, Python lock, renderer-build lock, renderer artifact, wheelhouse, `pip inspect`, and `pip freeze` provenance hashes recorded above. All nine native artifact hashes matched the local sample table in `Docs/DEPENDENCY_EVIDENCE.md`.
- Native runtime observation: exit `0`; wall time `22.392221032` seconds; user CPU `21.950268` seconds; system CPU `0.526766` seconds; maximum RSS `297016 KiB`; peak `3` procfs threads; `2` available CPUs. These are runner observations, not organizer ceilings.
- Logs included Fontconfig configuration, warning-only off-canvas self-check, and missing-asset renderer warnings. They are not contract-validation evidence.

## PR-head native x86_64 evidence

GitHub Actions run [40229964417](https://github.com/bjornefisk/ProjectChameleon/actions/runs/40229964417) passed `Verify and test` on PR head `b004f609c70440a510ceae645b8ff5de66afb071`. The job ran Ubuntu 24.04.5 `x86_64`; its `linux/amd64` image ID was `sha256:e4db4bc65599ba1086b391c45a9f2a6c1eda4739d3a712c7f0b27537b1257fb2`.

- All three offline samples returned `SUCCESS`; malformed input returned `MALFORMED_INPUT`, exit `1`, and no output files. The nine JSON/PNG/marker hashes matched both the sample table and run `40228417003`; repeated-run and clean-cache comparisons passed.
- Native renderer imports and Skia/Pillow `ldd` closure passed without missing libraries. The apt, Python, renderer, wheelhouse, `pip inspect`, and `pip freeze` provenance hashes matched the values recorded under the earlier native run.
- SBOM artifact `12612674286` is SPDX-2.3, `chameleon-stage1`, with 220 packages, 4,861 relationships, and 3,614,257 extracted bytes; SHA-256 `75f9def29db2071372d1a7e2ea92fbadea9e1b99bfab073eded669341e796da1`, matching the run log. Compared with the earlier SBOM, the 219 non-container package records and all 4,039 file-name/checksum pairs were identical; root container identity and 726 generated file SPDX identifiers differed. SBOM hashes are per-build evidence, not a claim of byte-identical output.
- This run preceded the workflow's `ubuntu-24.04` pin. GitHub's [runner-image migration notice #14748](https://github.com/actions/runner-images/issues/14748), retrieved 2026-10-25, says `ubuntu-latest` is moving to Ubuntu 26; the pinned head still needs a required check.

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
- Environment side effect: the initial failed setup modified Python 3.11 user-site packages before the venv-symlink fix; prior package state is unknown, so no rollback was attempted.

- Checks not complete: PR-head run `40229964417` on `b004f609c70440a510ceae645b8ff5de66afb071` passed native `Verify and test` and its SPDX artifact was verified. The current `ubuntu-24.04` runner-pin change still needs a passing required check; repository-maintainer review is also pending.

- Environment or platform limitation: local host is Darwin arm64; Buildx uses amd64 emulation. This does not prove native Linux/amd64 behavior.

## Security and data notes

- Secrets or personal data: no credential value is included in this record or used as a dependency input. An initial diagnostic surfaced a Hugging Face credential; the repository owner was notified to rotate/revoke it.
- Untrusted inputs or external content: pinned package/source inputs were hash/signature verified; sample designs are repository fixtures.
- Network boundary: dependency preparation/build requires network access to retrieve pinned sources/wheels/debs; the container runtime checks use `--network none`.

## Decision and handoff

- Decision: runs `40228417003` and `40229964417` passed native x86_64 checks and their SPDX artifacts were verified. Do not merge until the updated runner-pinned PR head passes the required check and the requested maintainer review is complete.
- Rollback/migration: revert the Issue #71 PR; old `requirements.txt` is removed as part of the clean cutover to reviewed lock inputs.
- Next owner: PR maintainer/reviewer and native GitHub Actions runner.
- Next concrete action: commit and push the runner pin and updated evidence, verify the new PR-head `Verify and test` result, and process the requested maintainer review before merging.
