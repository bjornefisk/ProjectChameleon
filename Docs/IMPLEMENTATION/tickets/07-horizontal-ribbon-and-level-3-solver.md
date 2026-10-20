# 07: Horizontal Ribbon Topology and Level 3 Extreme Leaderboard Solver

**What to build:**  
A horizontal ribbon layout generator and spatial compression engine for Level 3 ($1080 \times 1350 \to 728 \times 90$) and other extreme aspect ratios. The solver packs source groups along the primary horizontal axis using inferred source order and relationships, not a universal logo/headline/product/CTA slot order. It proactively compresses text toward the readable preference near $10$–$12\text{px}$ unless the source is smaller, scales down artwork isotropically, preserves rotated elements, and handles missing assets without crashing or replacing files. It must fail through the typed protocol if no hard-valid candidate exists after the permitted feasibility levers are exhausted.

**Blocked by:**  
`06: Multi-Signal Role Inference and Level 2 Column Pivot Solver`

**Status:**
active-review-sample-acceptance-gap

**Dispatch gate:** PR #14 is merged and `Docs/STATUS.md` records Ticket 06 as complete. Ticket 07 implementation is active on `feat/ticket-07-horizontal-ribbon-level3`; the public Level 3 sample-pass criterion remains unresolved. The implementation MUST remain contract-first and fail closed when its bounded candidates cannot satisfy hard validation.

- [x] Create `chameleon/engine/layout/horizontal_ribbon.py` implementing horizontal ribbon layouts for extreme wide-and-short formats: allocate source-aware horizontal slots while fitting within tight vertical height constraints.
- [x] Create `chameleon/engine/layout/vertical_restack.py` implementing vertical re-stacking for extreme tall-and-narrow formats.
- [x] Implement bounded spatial compression: search renderer-valid integer font sizes toward the readable preference near $10$–$12\text{px}$ unless the source is smaller, never below the schema minimum of `1`, scale foreground artwork isotropically, and tighten margins so elements fit without collision before reporting a typed failure.
- [x] Maintain rotated elements (e.g. `ribbon_bg` and `ribbon_label` rotated at $-12^\circ$): compute rotated bounding boxes and ensure they fit within the canvas and do not collide with adjacent elements.
- [x] Handle missing asset references (e.g. `holiday_watermark` referencing missing `solstice_holiday_badge_2025.png`): retain exact records, position them when a candidate exists, and delegate diagnostic warning behavior to the renderer without crashing or substituting pixel files.
- [x] Wire the horizontal ribbon generator into `chameleon/engine/resize.py` as a source- and target-aware candidate family for extreme wide targets. Do not make an unqualified fixed $\Delta_{\text{AR}}$ threshold the routing contract; keep other topology candidates available until hard validation.
- [ ] Verify that `chameleon_sample_level3_advanced.json` passes full semantic validation and renders a compliant $728 \times 90$ preview PNG without overlapping text or clipped boundaries. Current evidence is typed `INCOMPLETE_SEARCH` with no output pair; this is the open review gap, not a waived acceptance criterion.
- [x] Add integration tests in `chameleon/tests/layout/test_level3.py` for feasible horizontal/vertical candidates, rotated-group containment, deterministic rendering, source preservation, and the public sample's fail-closed boundary.
