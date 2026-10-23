# Agent run record

```text
run_id: issue-71-provenance-inventory-20261023
parent_task_id: issue-71
lead owner/role: @gabegaines24 / issue manager
started/updated: 2026-10-23
current workflow/gate: PR 74 draft evidence slice
source input revision: 2548c828cfafea7e03f28644b026665856e8dd0a
evidence capture commit: f8953ee058205601a4eaa78f57cc68b6e3db58df

## Outcome and acceptance

Recorded the current Docker, Python, renderer, schema, asset, and font inputs
for Issue #71. Required native amd64 CI evidence now passes for this candidate.
This slice does not claim apt closure, wheelhouse reproducibility, cross-platform
parity, or release qualification.

## Authority/ADR impact

No contract, schema, Docker, requirements, runtime, renderer, solver, or model
behavior changed. The evidence follows ADR-004 and `PROJECT_CONTRACT.md` §9.
A package-lock strategy remains a pending reviewed decision.

## Risk/data classification

High supply-chain and release-reproducibility risk. No private data or hidden
evaluation inputs were accessed.

## Integration owner

Repository maintainer and release manager.

## Capabilities available/unavailable

- Available: local Docker Desktop, Buildx, repository verifier, offline container.
- Host: Darwin arm64.
- Native amd64 CI qualification: available through GitHub Actions; unavailable locally.
- Organizer package-lock policy and official limits: unavailable.

## Integration checks

- `git diff --check` — passed.
- `make verify PYTHON_BOOTSTRAP=python3` — passed.
- `docker buildx build --platform linux/amd64 --load -t chameleon-issue71 .` — passed; Docker emitted the existing constant `FROM --platform` warning.
- `docker run --rm --network none ... chameleon-issue71` — passed; all three samples returned `SUCCESS` and produced six JSON/PNG files in a temporary output mount.
- `docker image inspect chameleon-issue71` — observed `linux/amd64`, image ID `sha256:2e7978e7b0285712eb6882234fb2e73ff330e31b837c86b3743a192d4b2d34ae`, size `1244208873` bytes.
- Offline renderer import — passed with Python `3.11.11`, machine `x86_64`, pinned `cr_renderer`, and `skia`.
- Local Skia/Pillow `ldd` closure check — passed with no `not found` output.

- GitHub Actions run [39988562284](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39988562284), job `120534271651` — passed on merge ref `3d7cd77926a5da744fa3cc70133c7c453cdd92c4`, including branch head `f8953ee058205601a4eaa78f57cc68b6e3db58df`.
- Native image — `linux/amd64`, ID `sha256:c77cd521c2b8424d1100186d97ae179d2a04fd48062f2cfcd6f8eaac890426b3`, size `896530714` bytes.
- Syft `v1.42.3` SPDX SBOM — non-empty, SHA-256 `364bb078cf090a0004ee1b281602cc5ef9e65a1363b378d4ba34d3b9cd47914d`.
- Native offline smoke — all three samples returned `SUCCESS`; repeated and clean-cache JSON/PNG/marker hashes matched.
- Native runtime — return code `0`, elapsed `17.614067901` seconds, user CPU `17.136705` seconds, system CPU `0.465883` seconds, maximum RSS `313644 KiB`, peak `3` procfs threads, and `2` available CPUs.
- Native renderer imports and Skia/Pillow `ldd` closure — passed with no `not found` entries.

## Failures/abandoned work/unrun checks

- The first Docker build attempt failed because Docker Desktop was stopped.
  Docker Desktop was started, and the same build then passed.
- Local native amd64 qualification, apt version closure, complete wheelhouse hash
  closure, and cross-platform parity were not run locally.
- Native amd64 CI, clean-cache rebuild, SBOM capture, and repeated artifact
  parity passed in run `39988562284`.
- No dependency or packaging change was attempted without an approved lock
  strategy.

## Security or external-fact notes

Apt package versions, complete transitive wheel hashes, cross-platform parity,
organizer resource limits, and release qualification remain
`UNVERIFIED_EXTERNAL_FACT`. The image ran with `--network none`; no runtime
download was permitted.

## Next concrete action/owner

Owner: `@gabegaines24`. Approve a package-lock strategy, then collect complete
apt and wheelhouse closure evidence. Do not change dependency or packaging
inputs before that decision.
