# 07: Horizontal Ribbon Topology and Level 3 Extreme Leaderboard Solver

**What to build:**  
A horizontal ribbon layout generator and spatial compression engine for Level 3 ($1080 \times 1350 \to 728 \times 90$) and other extreme aspect ratios. The solver packs source groups along the primary horizontal axis using inferred source order and relationships, not a universal logo/headline/product/CTA slot order. It treats roughly $10$–$12\text{px}$ as a readability preference, not a floor; any smaller positive size must pass the pinned renderer's hard checks and be reviewed for qualitative legibility. It scales artwork isotropically, preserves rotated elements, and handles missing assets without crashing or replacing files. It must fail through the typed protocol if no hard-valid candidate exists after the permitted feasibility levers are exhausted.

**Dependency:**
`06: Multi-Signal Role Inference and Level 2 Column Pivot Solver` — ✅ COMPLETE

**Status:**
The bounded horizontal-ribbon and vertical-restack families remain within the four-topology / twelve-candidate search. Issue #61 adds a source-PDF-grounded, renderer-measured copy-band candidate; the public Level 3 sample publishes a hard-valid JSON/PNG pair in repeated local integration tests. Font probes and each grouped-text scale-refinement invocation are capped at 74 steps; cutoff work is reported and remains typed `INCOMPLETE_SEARCH`, never infeasibility. Superseding decisions ADR-010 through ADR-012 preserve one common quantized group transform, remove the unsupported numeric readability floor, and keep actual glyphs inside unchanged declared bounds. Required native x86_64 CI run 39711973748 passed on PR head `33f6fd9`; PR #65 is merged and the issue closed. The owner waived partner review; no partner approval is recorded; official scoring remains unverified.

**Current evidence:**
See [`Docs/STATUS.md`](../../STATUS.md) and [`Docs/IMPLEMENTATION/tickets/08-heldout-evaluation.md`](08-heldout-evaluation.md) for current local results and explicit native-amd64/organizer qualification boundaries.

**Dispatch gate:**
Ticket 06 is complete. The public sample now passes through Issue #61 and Accepted ADR-010 through ADR-012; PR #65 merged the bounded fix, and Issue #61 is closed. Keep this slice bounded, do not broaden it into solver dependencies, altered wire fields, or organizer-qualification claims.

The checklist below is the historical implementation proposal; the current disposition and evidence above supersede its unchecked starter-state wording.

- [ ] Create `chameleon/engine/layout/horizontal_ribbon.py` implementing horizontal ribbon layouts for extreme wide-and-short formats: allocate horizontal slots along the width while fitting within tight vertical height constraints.
- [ ] Create `chameleon/engine/layout/vertical_restack.py` implementing vertical re-stacking for extreme tall-and-narrow formats.
- [ ] Implement proactive spatial compression: when space is constrained, search font sizes toward the readable preference near $10$–$12\text{px}$ unless the source is smaller, never below the schema minimum of `1`, scale foreground artwork isotropically, and tighten margins so elements fit without collision before reporting a typed failure.
- [ ] Maintain rotated elements (e.g. `ribbon_bg` and `ribbon_label` rotated at $-12^\circ$): compute rotated bounding boxes and ensure they fit within the canvas and do not collide with adjacent elements.
- [ ] Handle missing asset references (e.g. `holiday_watermark` referencing missing `solstice_holiday_badge_2025.png`): retain the exact element record, position it within the layout, and emit a diagnostic warning without crashing or substituting pixel files.
- [ ] Wire the horizontal ribbon generator into `chameleon/engine/resize.py` as a source- and target-aware candidate family for extreme wide targets. Do not make an unqualified fixed $\Delta_{\text{AR}}$ threshold the routing contract; keep other topology candidates available until hard validation and ranking.
- [ ] Verify that `chameleon_sample_level3_advanced.json` passes full semantic validation and renders a compliant $728 \times 90$ preview PNG without overlapping text or clipped boundaries.
- [ ] Add integration tests in `chameleon/tests/layout/test_level3.py`.
