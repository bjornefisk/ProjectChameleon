# Artifact conformance fixtures

These small designs exist to be rendered by the pinned adapter and then judged by `engine.artifact.validate_artifact`. Each one isolates a class of renderer behavior. They are source-valid designs (`validate_source` accepts them) that use only the committed `brand_kit` assets and fonts.

- `composite.json`: an opaque cover background, an exactly copied rounded rectangle with a stroke, an exactly copied `contain` image with transparent margins, an ellipse, a 35 % translucent overlay, and text. This covers every kind of draw the validator distinguishes (exact copies, a translucent blend, and text).
- `missing_asset.json`: an image whose asset is absent. The adapter draws its deterministic placeholder and must warn; the validator accepts the placeholder only with that warning.
- `large_canvas.json`: a 2100x1400 canvas that the renderer downscales to 2048x1365, so every draw is resampled and bounds are measured in pixel coordinates.
- `bleed_overlap.json`: shapes that bleed off the canvas on several sides and overlap each other, to catch clipping and obstruction mistakes that would reject a legitimate render.
- `low_contrast_text.json`: near-white text on the white canvas. Contrast is a soft ranking term and must never decide hard validity.

The validator replays fully opaque, integral, unrotated one-to-one image and shape pixels from adapter rasters. For every non-exact layer it bounds-checks against the adapter-derived paint region and compares the decoded output with a second render from the pinned adapter; this covers text, rotated, translucent, partially transparent, and downscaled pixels without accepting arbitrary antialiasing or exterior ink. PNG container metadata is outside semantic validation; staging still requires a readable PNG. Soft contrast remains outside this hard gate.
