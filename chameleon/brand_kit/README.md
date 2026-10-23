# Solstice brand kit — placeholder assets

These are **stand-in** assets and fonts, generated to unblock rendering and
testing of the 3 sample designs (Level 1/2/3) right now. They are NOT final
production brand assets.

## assets/ (3 files, referenced by `asset_id` in the sample JSONs)

| File | Used as |
|---|---|
| `solstice_bg_gradient.png` | full-bleed background (`fit: cover`) |
| `solstice_logo_lockup.png` | logo (`fit: contain`) — transparent background, white wordmark: invisible against a white viewer, composite onto a dark canvas to check it |
| `solstice_bottle.png` | product image (`fit: contain`) — transparent background |

Do NOT add a `solstice_holiday_badge_2025.png` here — that filename is
intentionally missing in the Level 3 sample, to test that the renderer
handles a missing asset gracefully instead of crashing.

## fonts/ (7 files, matching the `font_family` values in the schema)

- `SolsticeSerif-Regular.ttf`, `SolsticeSerif-Bold.ttf`, `SolsticeSerif-Italic.ttf`
  (Lora 3.008 faces under SIL OFL 1.1; the Lora reserved primary name is replaced.)
- `SolsticeSans-Regular.ttf`, `SolsticeSans-Bold.ttf`, `SolsticeSans-Italic.ttf`,
  `SolsticeSans-BoldItalic.ttf`
  (Poppins 4.004 faces under SIL OFL 1.1.)

Full source license texts ship beside the font files as `OFL-Lora.txt` and
`OFL-Poppins.txt`. Embedded family/style/weight names were checked against each
face; the project loader derives exact faces from the renamed filenames and
fails closed for missing combinations. Provenance, license conditions, hashes,
and checked-sample glyph coverage are recorded in
[`../../Docs/DEPENDENCY_EVIDENCE.md`](../../Docs/DEPENDENCY_EVIDENCE.md).

## Before this goes out to students

Swap this whole folder for the real thing once available:
- actual Solstice brand illustration assets (from the source design files,
  not a flattened poster crop)
- actual Adobe/Solstice brand font files, licensed for redistribution

Both are drop-in replacements — same filenames, same `asset_id`/`font_family`
values, nothing else needs to change.
