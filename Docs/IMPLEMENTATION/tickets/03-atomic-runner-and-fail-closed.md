# 03: Atomic Batch Staging and Fail-Closed Runner

**What to build:**  
A resilient batch orchestrator and task execution harness in `chameleon/engine/main.py` that isolates tasks, guarantees atomic pair publication (JSON and PNG are published together or not at all), cleans up stale artifacts on failure, catches typed errors, and ensures exit code `0` is returned if and only if every task in the batch succeeds.

**Blocked by:**  
`01: Semantic Contract Validator and Failure Reason Codes`

**Status:**  
ready-for-agent

- [ ] Create `chameleon/engine/staging.py` providing task staging primitives: creates temporary files `<task>_output.json.tmp` and `<task>_output.png.tmp`, validates both, and commits them atomically to their final paths.
- [ ] Implement stale artifact cleanup in `staging.py`: if a task fails or raises an error, remove any pre-existing `<task>_output.json` and `<task>_output.png` so stale outputs from prior runs are never scored.
- [ ] Update `chameleon/engine/main.py` to use `staging.py` for all task processing.
- [ ] Wrap `resize()` invocation with typed error handling: catch `InfeasibleLayoutError` and log the exact reason code without crashing the entire batch process.
- [ ] Ensure that independent tasks continue processing after a single task fails, collecting complete batch diagnostics.
- [ ] Update exit code logic in `main.py`: return exit status `0` if and only if all discovered task files successfully produced and committed their output pair; return nonzero if any task failed, encountered malformed input, or raised an error.
- [ ] Add integration tests under `chameleon/tests/engine/test_runner.py` verifying that valid tasks publish pairs, invalid/infeasible tasks produce zero output files, and batch exit codes correctly reflect partial vs. complete success.
