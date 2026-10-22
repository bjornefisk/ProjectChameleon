# Run briefing: main synchronization and Docker smoke

## Executive status

**Result: local and Docker end-to-end paths pass.**

- Active branch is `main`.
- Local `main` matches `origin/main`.
- `git pull origin main` returns `Already up to date.`
- Repository-local pull policy is `pull.ff=only`.
- All three checked-in sample tasks return `SUCCESS` in the Docker runtime.
- Each successful task publishes a JSON/PNG pair and hidden commit marker.
- No product source files changed during this run.
- This Docker run uses `linux/amd64` emulation on an arm64 host. It is not native-amd64 qualification.

## Root cause and branch decision

The failed pull happened because the shell was on `integration/pr-remediation`, while `main` was behind `origin/main`.

At inspection time:

- `integration/pr-remediation`: 21 commits ahead and 14 commits behind `origin/main`.
- Local `main`: 14 commits behind `origin/main`.

Actions taken:

1. Switched the worktree to `main`.
2. Fast-forwarded local `main` with `git pull --ff-only origin main`.
3. Set `pull.ff=only` for this repository.
4. Confirmed `git pull origin main` is up to date.
5. Left non-main branches untouched. Delete them only after owners confirm no work remains.

Use `main` as the integration branch. Do not merge the stale remediation branch without reviewing its unique commits.

## Program input and output

The engine ingests JSON files from `chameleon/input/`. Markdown files under `.agents/` guide the team; they are not engine input.

Docker processed all three checked-in tasks:

| Task | Target canvas | Source records | Result | Published artifacts |
|---|---:|---:|---|---|
| `chameleon_sample_level1_warmup.json` | `1080 x 1350` | 4 | `SUCCESS` | JSON, PNG, commit marker |
| `chameleon_sample_level2_core.json` | `1600 x 400` | 11 | `SUCCESS` | JSON, PNG, commit marker |
| `chameleon_sample_level3_advanced.json` | `728 x 90` | 17 | `SUCCESS` | JSON, PNG, commit marker |

`make inspect` passed for all three outputs. It reported zero unintended foreground collisions.

The Level 3 output preserved all 17 source records and retained the missing asset reference for `solstice_holiday_badge_2025.png`.

## Commands and observed results

| Command | Result | Evidence |
|---|---|---|
| `docker info --format '{{.ServerVersion}} {{.OSType}}/{{.Architecture}}'` | Pass | Docker `29.9.2`, `linux/aarch64` host runtime |
| `docker buildx version` | Pass | Buildx `v0.38.1` |
| `make docker-build` | Pass | `linux/amd64` image `sha256:4bdd50458093bfccb0d67d8a15e9e1d4f3d66ebae47340709524091fe03acf67` |
| `make docker-test` | Pass | Offline run; all three tasks `SUCCESS` |
| `make inspect` | Pass | All JSON/PNG/marker pairs authorized; no unintended collisions |
| `make verify && make preflight` | Pass | Repository governance and wiring checks passed |
| `../.venv/bin/python -m engine.main` | Pass | Local run; all three tasks `SUCCESS` |
| `make test PYTHON=/tmp/chameleon-pinned-venv/bin/python` | Partial | 273/275 passed; two persisted Darwin-arm64 PNG hash checks failed |
| `../.venv/bin/python -m unittest scripts.test_review_pr -v` | Pass | 47/47 review tests passed |

The documented bare command `python -m engine.main` was unavailable because this shell has no `python` executable. Use the project interpreter path or `make run`.

## Warnings and interpretation

These warnings did not fail the run:

- `FromPlatformFlagConstDisallowed`: Dockerfile uses a constant `FROM --platform=linux/amd64`.
- Host platform mismatch: the amd64 image runs through arm64 emulation.
- Fontconfig emitted an unknown `reset-dirs` element warning.
- The non-authoritative self-check reports expected off-canvas source bleed for `deco_circle_1`.
- The renderer emits a diagnostic placeholder warning for the missing holiday asset. The response keeps the original asset ID.

Hard validation and artifact inspection passed. These warnings do not prove native-amd64 parity or organizer acceptance.

## Test caveats

The default root `.venv` has `skia-python 144.0.post2`, while `chameleon/requirements.txt` pins `skia-python==132.0b11`. Its full suite result was 272/275 passing.

The temporary pinned Python 3.12 environment uses the required `skia-python==132.0b11`. Its remaining two failures are persisted Darwin-arm64 PNG hash mismatches:

- Renderer corpus: `right_negative_spacing`.
- Engine artifact evidence: `chameleon_sample_level1_warmup`.

Do not refresh persisted hashes just to silence tests. First decide which platform and dependency environment owns local evidence, then rerun and document intentional hash changes.

## Team handoff

### Keep

- `main` as the integration branch.
- `pull.ff=only` for this repository.
- JSON/PNG pair publication with commit markers.
- Missing-asset preservation and fail-closed contract behavior.
- Separate hard-validation evidence from visual quality and organizer scoring.

### Do next

1. Use `main` for shared work.
2. Start from a clean `main` pull before new changes:

   ```bash
   git switch main
   git pull --ff-only origin main
   ```

3. Re-run the Docker smoke sequence after source changes:

   ```bash
   make docker-build
   make docker-test
   make inspect
   ```

4. Resolve persisted Darwin hash evidence through an intentional, reviewed evidence update.
5. Keep native-amd64, cross-platform parity, organizer-held-out scoring, and official release qualification marked unverified.

## Current conclusion

The branch problem is fixed. The engine processes every checked-in sample successfully in the offline `linux/amd64` container. Remaining work is evidence qualification, not a demonstrated runtime failure.
