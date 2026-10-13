# 03: Atomic Batch Staging and Fail-Closed Runner

**What to build:**  
A resilient batch orchestrator and task execution harness in `chameleon/engine/main.py` that preserves exact numeric input tokens before validation and geometry, isolates tasks, guarantees atomic pair publication (JSON and PNG are published together or not at all), cleans up stale artifacts on failure, catches typed errors, and ensures exit code `0` is returned if and only if every task in the batch succeeds.

**Blocked by:**  
`01: Semantic Contract Validator and Failure Reason Codes`

**Status:**  
implemented — focused runner integration evidence recorded below

- [x] Create `chameleon/engine/staging.py` providing task staging primitives: creates temporary JSON/PNG files and a hidden commit manifest with both staged-file hashes, then publishes the pair only after the manifest authorizes both final files.
- [x] Implement stale artifact cleanup in `staging.py`: if a task fails or raises an error, remove pre-existing final, temporary, and commit-manifest paths so stale outputs are never scored.
- [x] Update `chameleon/engine/main.py` to use `staging.py` for all task processing.
- [x] Configure task JSON decoding with `parse_int=int`, `parse_float=Decimal`, and a rejecting `parse_constant` hook (or an equivalent decoder) before any binary-float conversion; add runner-seam regression cases for finite decimal, exponent, and non-finite-constant values.
- [x] Wrap `resize()` invocation with typed error handling: catch `InfeasibleLayoutError` and log the exact reason code without crashing the entire batch process.
- [x] Ensure that independent tasks continue processing after a single task fails, collecting complete batch diagnostics.
- [x] Update exit code logic in `main.py`: return exit status `0` if and only if all discovered task files successfully produced and committed their output pair; return nonzero if any task failed, encountered malformed input, or raised an error.
- [x] Add integration tests under `chameleon/tests/runner/test_runner.py` verifying valid publication, marker-gated pair visibility, invalid/infeasible tasks, renderer and filesystem failures, exact numeric ingress, target validation, continuation, and aggregate exit status.

**Verification evidence:**

- `cd chameleon && ../.venv/bin/python -m unittest tests.runner.test_runner -v` — 17 tests passed.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` — 45 tests passed.
- `python3 scripts/verify_repository.py` — passed.
- Coverage includes marker-gated JSON/PNG publication, interrupted-commit cleanup, stale final/temp/marker cleanup, staging cleanup-error reporting, renderer import and PNG failures, typed infeasibility, malformed/non-finite input, exact target validation, Decimal decimal/exponent ingress, cleanup-failure continuation, and aggregate exit status.
