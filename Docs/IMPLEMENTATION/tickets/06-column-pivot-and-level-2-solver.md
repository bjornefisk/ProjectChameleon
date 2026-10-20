# 06: Multi-Signal Role Inference and Level 2 Column Pivot Solver

**What to build:**  
A bounded deterministic multi-signal role-inference engine and source-aware column-pivot topology generator for Level 2 ($1080 \times 1080 \to 1600 \times 400$). The solver may pivot vertical element stacks into side-by-side columns (for example, hero image on one side and headline/copy/CTA on the other), lock grouped button and badge units together via uniform group transforms, respect intentional translucent corner bleed, and avoid collisions between source-separated elements. It MUST preserve Stage 1 identity, immutable fields, exact ratios, rotated bounds, text/render bounds, missing assets, fail-closed behavior, offline runtime, and no generated/replaced pixels.

**Blocked by:**
- `05: Safe Geometry Baseline and Level 1 Near-Isomorphic Solver` ✅ COMPLETE

**Status:**
complete — merged into `main` by PR #14 at commit `58b697a`; focused/full/sample evidence recorded

**Issue and ownership:**
GitHub issue #13 — owner @bjornefisk; partner reviewer @gabegaines24

**Implementation provenance:**
historical source branch `feat/ticket-06-column-pivot-level2`, refreshed PR #14 source revision `2166392`, based on transition revision `77b3368` (`origin/work/pr-12-ready`); current main merge commit `58b697a`

**Dispatch gate (COMPLETE):**
Gate 1 qualification and Ticket 05 completion are recorded in [`Docs/STATUS.md`](../../STATUS.md). Ticket 06 implementation, merge, focused/full evidence, and Level 2 sample evidence are recorded. Exact column-pivot serialization and renderer-aware response text validation are current contract paths. Native-amd64, cross-platform hash parity, apt locks, and wheelhouse closure remain qualification gaps.

- [x] Create `chameleon/engine/layout/roles.py` implementing deterministic multi-signal role inference: classify background, logo, hero product art, primary headline, supporting text, button/badge assemblies, and decorative shapes using geometric coverage, layer indices, opacity, and type properties.
- [x] Create `chameleon/engine/layout/column_pivot.py` implementing column-pivot layouts for wide targets: divide horizontal space into proportional column slots (e.g. left media slot, right copy/action slot) based on source group extents.
- [x] Place grouped elements (e.g. `badge_bg` + `badge_label`, `cta_bg` + `cta_label`) using uniform group transforms, ensuring text labels remain centered and aligned within their shape backplates.
- [x] Implement source-bleed handling for decorative shapes (e.g. `deco_circle_1`), allowing them to maintain their corner bleed on the target canvas without violating containment rules.
- [x] Preserve source-intended overlaps (layered translucent shapes, buttons on backgrounds) while enforcing separation between elements that did not overlap in the source.
- [x] Wire the column-pivot generator into `chameleon/engine/resize.py` as a source- and target-aware candidate family for wide targets. Do not make an unqualified fixed $\Delta_{\text{AR}}$ threshold the routing contract; keep other topology candidates available until hard validation and ranking.
- [x] Verify that `chameleon_sample_level2_core.json` passes full semantic validation and renders a clean, uncrowded $1600 \times 400$ banner.
- [x] Add integration tests in `chameleon/tests/layout/test_level2.py`.

**Acceptance state:** Ticket 06 is complete within its bounded scope. PR #14 merged the role inference, column-pivot topology, readable-floor font search, relationship view, resource-guard removal, and evidence corrections. Follow-up hardening preserves exact geometry until one final serialization step and makes `validate_response()` invoke renderer-aware text preflight. Ticket 07/08, full candidate ranking, held-out evaluation, models/model weights, CP-SAT/OR-Tools, unapproved dependencies/schema/API changes, source shedding/hiding, opacity-zero or zero-size workarounds, copy revision, font substitution, finale behavior, horizontal ribbon, and vertical restack remain out of scope.


[You have received this identical output 3 times. Re-reading '/Users/charliefurlow/Desktop/ProjectChameleon/Docs/IMPLEMENTATION/tickets/06-column-pivot-and-level-2-solver.md:raw' will not change it — use a narrower selector (path:A-B), or proceed with the edit.]