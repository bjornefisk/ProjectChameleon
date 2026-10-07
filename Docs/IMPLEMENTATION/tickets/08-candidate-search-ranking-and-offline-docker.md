# 08: Bounded Macro-Search, Fixed-Point Ranking, and Offline Docker Qualification

**What to build:**  
The complete macro-candidate search and ranking pipeline coordinating all four layout topologies, paired with full qualification inside the offline `linux/amd64` Docker container. For any task, the engine generates up to 12 valid candidates across the four families, validates each through the actual renderer, ranks survivors with deterministic fixed-point scores, selects the optimal design, and qualifies cleanly in Docker with `--network none`.

**Blocked by:**  
`07: Horizontal Ribbon Topology and Level 3 Extreme Leaderboard Solver`

**Status:**  
ready-for-agent

- [ ] Create `chameleon/engine/layout/search.py` orchestrating candidate generation across the four topology families (near-isomorphic, column-pivot, horizontal-ribbon, vertical-restack) with at most 3 source-derived variants each (maximum 12 macro-candidates).
- [ ] Connect renderer-in-the-loop hard validation: pass every candidate through Skia rendering and `validate_response()`, immediately discarding any candidate that violates containment, ratios, groups, or text bounds.
- [ ] Create `chameleon/engine/layout/ranking.py` implementing fixed-point quality scoring: score readability ($\text{Rea}$), visual balance ($\text{Bal}$), alignment ($\text{Ali}$), and hierarchy preservation.
- [ ] Implement deterministic lexicographic tie-breaking: `(hard_validity, quality_tuple, topology_order, candidate_index, source_order)` with zero random seeds.
- [ ] Wire the full search and ranking pipeline into `resize()` in `chameleon/engine/resize.py`.
- [ ] Execute `python -m engine.main` locally across all 3 public samples and contract fixtures, confirming 100% pass rate.
- [ ] Build the Docker container using `docker buildx build --platform linux/amd64 -t chameleon-stage1 .`.
- [ ] Run the container with `--network none` mounting input and output volumes: verify that all 3 levels produce scorable JSON and PNG pairs without network access in < 2.0s per design.
- [ ] Confirm that peak memory remains $< 500\text{ MB}$ RAM and the final Docker image is $< 8\text{ GB}$.
