# 03: Atomic Batch Staging and Fail-Closed Runner

**What to build:**  
A resilient batch orchestrator and task execution harness in `chameleon/engine/main.py` that preserves exact numeric input tokens before validation and geometry, isolates tasks, guarantees atomic pair publication (JSON and PNG are published together or not at all), cleans up stale artifacts on failure, catches typed errors, and ensures exit code `0` is returned if and only if every task in the batch succeeds.

**Blocked by:**  
`01: Semantic Contract Validator and Failure Reason Codes`

**Status:**  
partially implemented in `engine.main` by the PR 7 review fix; the dedicated staging module and accepted cutoff/search integration remain pending.

- [ ] Create `chameleon/engine/staging.py` providing task staging primitives: creates temporary files `<task>_output.json.tmp` and `<task>_output.png.tmp`, validates both, and commits them atomically to their final paths.
- [x] Implement stale artifact cleanup in `chameleon/engine/main.py`: if a task fails or raises an error, remove any pre-existing `<task>_output.json`, `<task>_output.png`, commit marker, and temporary paths so stale outputs from prior runs are never scored.
- [ ] Update `chameleon/engine/main.py` to use `staging.py` for all task processing.
- [x] Configure task JSON decoding with `parse_int=int`, `parse_float=Decimal`, and a rejecting `parse_constant` hook before any binary-float conversion; runner-seam regression cases cover finite decimal, exponent, and non-finite-constant values.
- [x] Wrap `resize()` invocation with typed error handling: catch `InfeasibleLayoutError` and log the exact reason code without crashing the entire batch process.
- [x] Ensure that independent tasks continue processing after a single task fails, collecting complete batch diagnostics.
- [x] Update exit code logic in `main.py`: return exit status `0` if and only if all discovered task files successfully produced and committed their output pair; return nonzero if any task failed, encountered malformed input, or raised an error.
- [x] Map input, layout, search, renderer, serialization, and setup failures to the accepted internal task statuses while preserving detailed reason codes in diagnostics; failed tasks publish neither artifact.
- [x] Add runner publication tests under `chameleon/tests/runner/test_main.py` verifying valid pairs, invalid/infeasible tasks, malformed PNGs, interruption cleanup, batch continuation, and aggregate exit status.
