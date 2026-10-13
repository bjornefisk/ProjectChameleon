# 03: Atomic Batch Staging and Fail-Closed Runner

**What to build:**  
A resilient batch orchestrator and task execution harness in `chameleon/engine/main.py` that preserves exact numeric input tokens before validation and geometry, isolates tasks, guarantees atomic pair publication (JSON and PNG are published together or not at all), cleans up stale artifacts on failure, catches typed errors, and ensures exit code `0` is returned if and only if every task in the batch succeeds.

**Blocked by:**  
`01: Semantic Contract Validator and Failure Reason Codes`

**Status:**  
implemented — focused runner integration evidence recorded below

- [x] Create `chameleon/engine/staging.py` providing task staging primitives: creates temporary files `<task>_output.json.tmp` and `<task>_output.png.tmp`, validates both, and commits them atomically to their final paths.
- [x] Implement stale artifact cleanup in `staging.py`: if a task fails or raises an error, remove any pre-existing `<task>_output.json` and `<task>_output.png` so stale outputs from prior runs are never scored.
- [x] Update `chameleon/engine/main.py` to use `staging.py` for all task processing.
- [x] Configure task JSON decoding with `parse_int=int`, `parse_float=Decimal`, and a rejecting `parse_constant` hook (or an equivalent decoder) before any binary-float conversion; add runner-seam regression cases for finite decimal, exponent, and non-finite-constant values.
- [x] Wrap `resize()` invocation with typed error handling: catch `InfeasibleLayoutError` and log the exact reason code without crashing the entire batch process.
- [x] Ensure that independent tasks continue processing after a single task fails, collecting complete batch diagnostics.
- [x] Update exit code logic in `main.py`: return exit status `0` if and only if all discovered task files successfully produced and committed their output pair; return nonzero if any task failed, encountered malformed input, or raised an error.
- [x] Add integration tests under `chameleon/tests/engine/test_runner.py` verifying that valid tasks publish pairs, invalid/infeasible tasks produce zero output files, and batch exit codes correctly reflect partial vs. complete success.

**Verification evidence:**

- `cd chameleon && ../.venv/bin/python -m unittest tests.engine.test_runner -v` — 7 tests passed.
- `cd chameleon && ../.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` — 35 tests passed.
- `python3 scripts/verify_repository.py` — passed.
- Coverage includes successful JSON/PNG pair publication, stale final and temporary cleanup after resize and renderer failures, typed infeasibility, malformed/non-finite input, Decimal decimal/exponent ingress, independent mixed-batch continuation, and complete versus partial aggregate exit status.
