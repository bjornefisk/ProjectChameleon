# 07: Horizontal Ribbon Topology and Level 3 Extreme Leaderboard Solver

**What to build:**  
A horizontal ribbon layout generator and spatial compression engine that solves Level 3 ($1080 \times 1350 \to 728 \times 90$) and extreme aspect ratios. The solver packs elements along the primary horizontal axis (logo $\to$ headline $\to$ badges $\to$ product $\to$ CTA), proactively compresses text font size toward the readable floor ($\ge 10\text{px}$), scales down artwork isotropically, preserves rotated elements (like banners/ribbons), and handles intentionally missing assets without crashing or replacing files.

**Blocked by:**  
`06: Multi-Signal Role Inference and Level 2 Column Pivot Solver`

**Status:**  
ready-for-agent

- [ ] Create `chameleon/engine/layout/horizontal_ribbon.py` implementing horizontal ribbon layouts for extreme wide-and-short formats: allocate horizontal slots along the width while fitting within tight vertical height constraints.
- [ ] Create `chameleon/engine/layout/vertical_restack.py` implementing vertical re-stacking for extreme tall-and-narrow formats.
- [ ] Implement proactive spatial compression: when vertical or horizontal space is constrained, binary-search font sizes down to the readable floor ($10\text{px}$–$12\text{px}$), scale foreground artwork isotropically to compact dimensions, and tighten margins so elements fit without collision.
- [ ] Maintain rotated elements (e.g. `ribbon_bg` and `ribbon_label` rotated at $-12^\circ$): compute rotated bounding boxes and ensure they fit within the canvas and do not collide with adjacent elements.
- [ ] Handle missing asset references (e.g. `holiday_watermark` referencing missing `solstice_holiday_badge_2025.png`): retain the exact element record, position it within the layout, and emit a diagnostic warning without crashing or substituting pixel files.
- [ ] Wire the horizontal ribbon generator into `chameleon/engine/resize.py` for extreme wide targets ($\Delta_{\text{AR}} > 1.0$).
- [ ] Verify that `chameleon_sample_level3_advanced.json` passes full semantic validation and renders a compliant $728 \times 90$ preview PNG without overlapping text or clipped boundaries.
- [ ] Add integration tests in `chameleon/tests/layout/test_level3.py`.
