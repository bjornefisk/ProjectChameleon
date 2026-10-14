# 03: Atomic Batch Staging and Fail-Closed Runner

**What to build:**  
A resilient batch orchestrator and task execution harness in `chameleon/engine/main.py` that preserves exact numeric input tokens before validation and geometry, isolates tasks, guarantees atomic pair publication (JSON and PNG are published together or not at all), cleans up stale artifacts on failure, catches typed errors, and ensures exit code `0` is returned if and only if every task in the batch succeeds.

**Blocked by:**  
`01: Semantic Contract Validator and Failure Reason Codes`

**Status:**  
implemented — focused runner integration evidence recorded below

- [x] Create `chameleon/engine/staging.py` providing task-private staging primitives, JSON/PNG validation, and a hidden commit manifest with both staged-file hashes; publish the marker last, and treat final files without a matching marker as uncommitted.
- [x] Implement stale artifact cleanup and quarantine in `staging.py`: if a task fails or raises an error, remove or move pre-existing final, temporary, commit-manifest, and private staging paths so stale outputs are never scored.
- [x] Update `chameleon/engine/main.py` to use `staging.py` for all task processing.
- [x] Configure task JSON decoding with `parse_int=int`, `parse_float=Decimal`, and a rejecting `parse_constant` hook (or an equivalent decoder) before any binary-float conversion; add runner-seam regression cases for finite decimal, exponent, and non-finite-constant values.
- [x] Wrap `resize()` invocation with typed error handling: catch `InfeasibleLayoutError` and log the exact reason code without crashing the entire batch process.
- [x] Ensure that independent tasks continue processing after a single task fails, collecting complete batch diagnostics.
- [x] Update exit code logic in `main.py`: return exit status `0` if and only if all discovered task files successfully produced and committed their output pair; return nonzero if any task failed, encountered malformed input, or raised an error.
- [x] Add runner-seam regression tests under `chameleon/tests/runner/` verifying valid publication, marker-gated pair visibility, half-even serialization, invalid/infeasible tasks, renderer and filesystem failures, exact numeric ingress, safe asset references, target validation, continuation, aggregate exit status, symlink/path-boundary rejection, stale-artifact reconciliation, and safe diagnostics.

**Verification evidence:**

- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests/runner -p 'test_*.py' -v` — 63 tests passed.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` — 113 tests passed.
- `python3 scripts/verify_repository.py`, `make verify`, `git diff --check`, and changed-file `py_compile` — passed.
- `cd chameleon && ../.venv/bin/python -m engine.main` — exited 1 and failed closed for all three sample tasks (`IMAGE_RATIO_VIOLATION` for Levels 1–2 and `CONTAINMENT_VIOLATION` for Level 3); output remained limited to `.gitkeep`.
- `cd chameleon && docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` — passed with the existing constant-platform warning; the matching offline container run exited 1 with the same typed baseline failures and left only `.gitkeep` (amd64 emulation on the arm64 workstation, not native-amd64 qualification).
- Coverage includes marker-gated JSON/PNG publication, post-publish manifest verification, interrupted-commit cleanup, stale final/temp/marker cleanup and quarantine (including invalid stems), cleanup-error reporting and continuation, invalid-filename continuation, renderer import and PNG failures, typed infeasibility/search statuses, malformed/non-finite input, exact target validation, Decimal decimal/exponent ingress, half-even serialization, input/output/final-artifact symlink rejection, task-name boundary checks, asset-root containment, source-qualified background inspection, positive-area collision inspection, orphan-artifact rejection, escaped diagnostics, and aggregate exit status.
