# 08: Bounded Macro-Search, Fixed-Point Ranking, and Offline Docker Qualification

**What to build:**
A bounded macro-candidate search coordinating all four layout topologies, paired with offline `linux/amd64` qualification. For any task, the engine generates at most 12 candidates across the four families, validates each through the actual renderer, ranks only hard-valid survivors, selects deterministically, and records qualification evidence rather than assuming every task is feasible.

**Dependency:**
`07: Horizontal Ribbon Topology and Level 3 Extreme Leaderboard Solver` supplies topology interfaces. Bounded Ticket 08 integration is present; Issue #61's public Level 3 pair is merged in PR #65, with the issue closed. Required native x86_64 CI passed on PR head `33f6fd9`; official held-out scoring and release qualification remain unverified.

**Status:**
implemented; local bounded evidence and native x86_64 CI recorded; PR #65 merged and Issue #61 closed. Cross-platform parity, organizer-held-out scoring, and release qualification remain unverified.

The checkboxes below preserve the earlier Ticket 08 evidence record. Current Issue #61 behavior and verification are recorded in [`../../STATUS.md`](../../STATUS.md); do not treat the historical Level 3 `INCOMPLETE_SEARCH` result below as current.

- [x] Create `chameleon/engine/layout/search.py` orchestrating candidate generation across the four topology families (near-isomorphic, column-pivot, horizontal-ribbon, vertical-restack) with at most 3 source-derived variants each (maximum 12 macro-candidates).
- [x] Connect renderer-in-the-loop hard validation: pass every candidate through Skia rendering and `validate_response()`, immediately discarding any candidate that violates containment, ratios, groups, or text bounds.
- [x] Create `chameleon/engine/layout/ranking.py` implementing fixed-point quality scoring: score readability ($\text{Rea}$), visual balance ($\text{Bal}$), alignment ($\text{Ali}$), and hierarchy preservation.
- [x] Implement deterministic lexicographic tie-breaking: `(hard_validity, quality_tuple, topology_order, candidate_index, source_order)` with zero random seeds.
- [x] Wire the full search and ranking pipeline into `resize()` in `chameleon/engine/resize.py`.
- [x] Execute `python -m engine.main` locally across all three public samples and contract fixtures, recording hard-validation results, typed failures, and deterministic artifacts. Do not claim a 100% pass rate until the implementation and fixture evidence establish it.
- [x] Build the Docker container using `docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .` so the image is available to the local `docker run` smoke step regardless of the selected Buildx driver.
- [x] Run the container with `--network none` mounting input and output volumes: record whether each level produces a valid JSON/PNG pair, any typed failure status, and measured per-design runtime against the <$2.0$ second performance target.
- [x] Measure peak memory against the <$500\text{ MB}$ solver target and image size against the <$8\text{ GB}$ container ceiling; record evidence rather than treating targets as completed qualification.

Evidence: [STATUS.md](../../STATUS.md) and [DEPENDENCY_EVIDENCE.md](../../DEPENDENCY_EVIDENCE.md)
