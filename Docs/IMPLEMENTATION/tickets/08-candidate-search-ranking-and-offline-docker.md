# 08: Bounded Macro-Search, Fixed-Point Ranking, and Offline Docker Qualification

**What to build:**  
A bounded macro-candidate search coordinating all four layout topologies, paired with offline `linux/amd64` qualification. For any task, the engine generates at most 12 candidates across the four families, validates each through the actual renderer, ranks only hard-valid survivors, selects deterministically, and records qualification evidence rather than assuming every task is feasible.

**Integrated dependency:**
Ticket 07 revision `b11d7c3` supplies horizontal-ribbon and vertical-restack exports.

**Status:**  
Bounded search implementation and local qualification are complete on the integrated PR #15 review stack.
Native-amd64, peak-RSS, held-out, and public Level 3 pass qualification remain incomplete or unverified.

## Integration ownership

Ticket 08 owns `chameleon/engine/resize.py` integration through `layout.search.search()`.
Ticket 07 owns horizontal-ribbon and vertical-restack modules and tests.
Topology exports use:
`solve_<topology>(source, target_canvas, *, font_manager=None, fonts_dir=None, assets_dir=None, variant=None, rendered_output=None) -> dict[str, Any]`.
The private `rendered_output` collector lets search reuse source-proportional solver PNG bytes.
Derived variants render after geometry changes; central serialized hard validation remains before and after rendering.
Revert the Ticket 07 dependency merge to roll back integrated topology ownership.

- [x] Create `chameleon/engine/layout/search.py` across four topology families with at most 12 macro-candidates.
- [x] Connect renderer-in-the-loop hard validation and serialized validation.
- [x] Create fixed-point quality scoring and deterministic lexicographic tie-breaking.
- [x] Wire search and ranking through `resize()`.
- [x] Run local public samples and record typed failure and artifact behavior.
- [x] Build and run the offline `linux/amd64` image under `--network none`.
- [ ] Run the contract fixture matrix and catalogue-sized synthetic target search qualification.
- [ ] Establish native-amd64 runtime and peak-memory qualification.
- [ ] Run held-out evaluation and repeated held-out determinism.
- [ ] Produce a hard-valid public Level 3 sample output.

Evidence: [08-qualification-evidence.md](08-qualification-evidence.md)
