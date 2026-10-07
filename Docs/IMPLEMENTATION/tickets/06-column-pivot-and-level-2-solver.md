# 06: Multi-Signal Role Inference and Level 2 Column Pivot Solver

**What to build:**  
A multi-signal role inference engine and column-pivot archetype generator that automatically solves Level 2 ($1080 \times 1080 \to 1600 \times 400$). The solver pivots vertical element stacks into side-by-side columns (e.g. hero image on one side, headline/copy/CTA on the other), locks grouped button and badge units together via uniform group transforms, respects intentional translucent corner bleed, and avoids collisions between source-separated elements.

**Blocked by:**  
`05: Safe Geometry Baseline and Level 1 Near-Isomorphic Solver`

**Status:**  
ready-for-agent

- [ ] Create `chameleon/engine/layout/roles.py` implementing deterministic multi-signal role inference: classify background, logo, hero product art, primary headline, supporting text, button/badge assemblies, and decorative shapes using geometric coverage, layer indices, opacity, and type properties.
- [ ] Create `chameleon/engine/layout/column_pivot.py` implementing column-pivot layouts for wide targets: divide horizontal space into proportional column slots (e.g. left media slot, right copy/action slot) based on source group extents.
- [ ] Place grouped elements (e.g. `badge_bg` + `badge_label`, `cta_bg` + `cta_label`) using uniform group transforms, ensuring text labels remain centered and aligned within their shape backplates.
- [ ] Implement source-bleed handling for decorative shapes (e.g. `deco_circle_1`), allowing them to maintain their corner bleed on the target canvas without violating containment rules.
- [ ] Preserve source-intended overlaps (layered translucent shapes, buttons on backgrounds) while enforcing separation between elements that did not overlap in the source.
- [ ] Wire the column-pivot generator into `chameleon/engine/resize.py` as a source- and target-aware candidate family for wide targets. Do not make an unqualified fixed $\Delta_{\text{AR}}$ threshold the routing contract; keep other topology candidates available until hard validation and ranking.
- [ ] Verify that `chameleon_sample_level2_core.json` passes full semantic validation and renders a clean, uncrowded $1600 \times 400$ banner.
- [ ] Add integration tests in `chameleon/tests/layout/test_level2.py`.
