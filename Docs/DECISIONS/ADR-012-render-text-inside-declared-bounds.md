# ADR-012: Align rendered text origins to actual glyph bounds

## Status

Accepted — the issue owner authorized this PDF-grounded decision and an independent reviewer returned APPROVE on 2026-10-21. Repository maintainer review of the implementation PR remains required before merge.

## Date / owner / reviewers

- Date: 2026-10-21
- Owner: @bjornefisk (issue owner/project authority)
- Reviewers: independent reviewer role (ADR proposal review, APPROVE, 2026-10-21); repository maintainer PR review pending

## Context / authority

The project contract §§6 and 8 and ADR-008 require the pinned renderer's actual glyph bounds to remain within each declared text element. The pinned `cr-renderer` line origin starts at `line_index * font_size * line_height`, then draws each blob at `y - metrics.fAscent`. In the packaged Solstice Sans faces, some glyph bounds extend slightly above that nominal line origin. The current converter rejects those glyphs even when the text box otherwise has sufficient room; increasing box height cannot fix a negative top bound.

The original challenge PDF §§2.3 and 2.5 requires the renderer to apply resized properties and requires readable, uncut text. It does not prescribe that the first glyph baseline be anchored exactly at the text rectangle's top coordinate. A minimal adapter-owned inset can place the actual glyph envelope inside the declared rectangle without changing the JSON response or weakening the glyph check.

## Decision

For each text element, use the exact packaged font faces, wrapped line map, integer `font_size`, line height, and letter spacing already used for rendering to compute the minimum glyph top across all non-empty glyph bounds. If no glyph bounds exist (including empty content or only forced empty lines), define the inset as zero. Otherwise define one internal vertical inset:

```text
inset = 0 if no glyph bounds; otherwise max(0, -minimum_glyph_top)
```

Add this inset to the transient renderer `top` for that text element and to the same positioned-glyph coordinates used by validation. Preserve every external element field, including serialized `y`, `height`, `font_size`, `line_height`, and content. Keep the existing line-origin spacing between lines. Reject if any adjusted glyph is outside the original declared box or if the existing line-count/line-box checks fail. Empty lines still count for the existing `max_lines` and line-box rules. The inset is not serialized, does not move siblings, and is never a clipping or overflow exemption.

The same conversion function and inset calculation are authoritative for candidate validation, artifact validation, and PNG rendering. If the inset is zero, rendered behavior is unchanged. The pinned upstream renderer and its dependency revision remain unchanged.

## Options considered

1. Keep rejecting any negative glyph top. Rejected: it treats the renderer's top-origin convention as a hard organizer constraint and makes box-height expansion unable to fix the failure.
2. Ignore negative tops in validation or add a tolerance. Rejected: it would admit actual glyphs outside the declared box.
3. Shift the transient renderer origin by exactly the measured amount and re-check the full glyph envelope. Selected: it preserves the hard bound while using an internal placement degree of freedom that does not change source data.

## Consequences / tradeoffs

- Some text raster pixels move down by a subpixel/internal inset relative to the element's serialized `y`; the visible ink remains inside its declared geometry.
- Text is still measured and rendered with the same pinned faces, line map, spacing, and upstream renderer. The inset does not change wrap widths or font selection.
- Reproducible output depends on the pinned font bytes and renderer metrics; native-amd64 and cross-platform PNG parity remain separate evidence gates.

## Security / dependency / data impact

No dependency, schema, runtime, network, source data, asset, or public API change. The adapter reads only packaged font bytes already in the offline runtime.

## Migration / rollback

Update the text contract/converter and all tests together. Roll back if validation and renderer consume different insets, if any glyph remains outside its box, if a source text's line spacing/content changes, or if artifact provenance fails. Fail closed rather than bypassing the actual-glyph check.

## Affected files / callers / docs

`Docs/PROJECT_CONTRACT.md` §§6 and 8; ADR-008 §§3–4; `chameleon/renderer/converter/convert.py`; renderer, contract, artifact, and layout tests; `chameleon/engine/layout/horizontal_ribbon.py`; `Docs/STATUS.md`; Ticket 07.

## Verification

Test faces with negative and non-negative first-line glyph tops, descenders, italic overhang, mixed style faces, forced empty lines, and multiple lines. Assert the adapter top offset equals the measured minimal inset, all glyph coordinates remain inside the declared box, source JSON remains unchanged, and the same converter output produces the expected PNG. Run public Level 3 validation and compare repeated response/PNG signatures.

## Supersedes

Extends ADR-008 §§3–4 only with the minimal transient first-line/element origin inset. Unicode-safe wrapping, style ranges, glyph-bound rejection, line-box/`max_lines` rules, and source-field immutability remain unchanged.

## Open external facts

The supplied PDF does not specify line-origin alignment. Final font licensing/metadata, organizer scoring, and native-amd64/cross-platform parity remain unverified.
