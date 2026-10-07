# Contract fixtures

These fixtures are deliberately small and test contract edges before the real solver exists.

- `empty_design.json`: valid empty source.
- `minimal_design.json`: required types, defaults, and private fixture annotation.
- `style_run_boundary.json`: external end-exclusive `[6, 15)` style range; the public Level 2 sample uses the same corrected boundary.
- `offcanvas_decoration.json`: the narrow translucent source-bleed exception.
- `image_ratio.json`: foreground `fit=fill` still requires source box ratio preservation.
- `infeasible_target.json`: task used to exercise the typed fail-closed path once the orchestrator handles it.

The three shipped `input/chameleon_sample_*.json` files remain the primary tier fixtures. Fixture files describe expected contract behavior; they do not make the current uniform-stretch baseline conforming.
