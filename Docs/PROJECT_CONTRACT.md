# Project Chameleon Project Contract

**Status:** Accepted Stage 1 contract; current implementation evidence and qualification boundaries are tracked in `Docs/STATUS.md`

**Contract version:** 1.0

**Design schema:** `chameleon/chameleon_design_schema_v0.9.json` (v0.9 is ratified for Stage 1; its identifier remains v0.9 for compatibility)

**Ratified:** 2026-10-06

This document is the normative behavioral contract for the autonomous Stage 1 retargeting engine. It resolves conflicts in the earlier design notes and starter comments. It defines the required behavior, not a claim that every environment is qualified; implementation and platform evidence are tracked separately in `Docs/STATUS.md`.

## 1. Scope

Stage 1 maps one source design and one target canvas to a target design without manual placement decisions:

```text
resize(source_design, target_canvas) -> target_design
```

The engine rearranges existing records. It does not flatten the design, generate pixels, rewrite copy, or call a runtime service. Stage 2/the finale is a separate interactive product contract; see [ADR-005](DECISIONS/ADR-005-separate-stage-1-from-finale.md).

## 2. Authority and conflict resolution

Use the following precedence. A lower item never silently overrides a higher item:

1. This contract and its **Accepted** ADRs.
2. The ratified JSON schema for structural syntax and field types.
3. The pinned project renderer adapter plus the pinned upstream `cr-renderer` source for delegated pixel behavior.
4. The challenge brief and `chameleon/RULES.md` for organizer-supplied scoring and submission restrictions, as clarified by this contract.
5. The sample inputs as conformance fixtures, not as authority for undocumented behavior.
6. Other `Docs/*.md` architecture and roadmap documents as proposed design guidance.
7. Starter implementation, comments, and warning-only self-checks. `engine/resize.py` is explicitly a deliberately incorrect baseline.

If two normative artifacts disagree, update the lower artifact or write a superseding ADR. Do not choose whichever document was read last.

## 3. Request and response

The batch task envelope is:

```json
{
  "source": {"canvas": {"width": 1080, "height": 1080}, "elements": []},
  "target_canvas": {"width": 1600, "height": 400}
}
```

Sample metadata (`task_id`, `difficulty`, `difficulty_label`, and `notes`) belongs to the harness. It is not part of a `DesignDocument` and is not copied into the response.

The public Stage 1 function receives `source` and `target_canvas` separately and returns one flat `DesignDocument`:

```json
{"canvas": {"width": 1600, "height": 400}, "elements": [...]}
```

The source object MUST NOT be mutated. The response canvas MUST equal `target_canvas` exactly. The response element array MUST have the same length, IDs, ID order, and one record per source record.

## 4. Structural data contract

`chameleon/chameleon_design_schema_v0.9.json` is the ratified wire schema for both source and response `DesignDocument` values.

- Canvas width and height are positive integers.
- `elements` MAY be empty. An empty source returns the target canvas and an empty element array.
- Element IDs are non-empty strings and MUST be unique in a task. The JSON Schema expresses the type; the future semantic validator and the solver conformance harness enforce uniqueness.
- Source-authored zero width/height records are valid and remain records. A positive-area source record MUST NOT be reduced to zero to remove it.
- Coordinates may be negative in source input because intentional decorative bleed is a supported fixture case. Output containment rules are in §7.
- JSON Schema `default` values are annotations; the engine MUST NOT add omitted fields to the response. The renderer applies these effective defaults:

| Field | Effective default |
| --- | --- |
| `rotation` | `0` degrees clockwise |
| `opacity` | `1` |
| `z_index` | `0` for render sorting only |
| `group_id` | `null` |
| `font_weight` / `font_style` | `regular` / `normal` |
| `text_align` | `left` |
| `line_height` / `letter_spacing` | `1.2` / `0` |
| `max_lines` / `style_runs` | `null` / `[]` |
| image `fit` | `contain` |
| shape `stroke_color` / `stroke_width` / `corner_radius` | `null` / `0` / `0` |

Fixture-only element annotations whose names start with `_` are allowed and are fixed opaque metadata. No other undeclared element or style-run fields are part of the contract.

## 5. Stage 1 mutability

Only these values may change:

| Location | Mutable value | Required rule |
| --- | --- | --- |
| response `canvas` | `width`, `height` | Equal to the target canvas |
| element | `x`, `y`, `width`, `height` | Finite integer pixel geometry; subject to ratio, group, and bounds rules |
| text element | `font_size` | Finite integer pixels, at least `1`; content and all other text properties stay fixed |

The following are immutable, including when they are inconvenient: element IDs and order, `type`, `rotation`, `opacity`, `z_index`, `group_id`, text content, font family/weight/style/color/alignment/line height/letter spacing/style runs, image `asset_id` and `fit`, shape fields, and fixture annotations. Omitted source fields remain omitted in the response.

The serializer MUST preserve finite JSON numeric tokens as exact decimal/rational values at ingress for contract calculations. It MUST use one documented round-half-even quantization step for mutable output geometry and text `font_size`; no intermediate geometry, ratio, group, or AABB value may be rounded. After serialization, the validator MUST re-read the serialized integers and recompute all bounds, ratios, group relationships, and hard checks. A candidate that only passes before this final serialization is invalid.

## 6. Renderer contract

The authoritative local render path is `chameleon/renderer/converter/` using `cr-renderer` commit [`a17e1fb9a732959dd6c21ae168d5ee09d74bd64f`](https://github.com/CyberAgentAILab/cr-renderer/commit/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f). The project dependency pins and source citations are recorded in [DEPENDENCY_EVIDENCE.md](DEPENDENCY_EVIDENCE.md).

### Layering and geometry

- The adapter stably sorts records by effective `z_index`; source array order breaks ties. This sorting is render-only; the response array order remains source order.
- The upstream renderer translates to `left`/`top`, then rotates around the local rectangle center in degrees.
- The upstream renderer maps the complete prepared image rectangle to the destination rectangle. It does not provide browser-style automatic fit behavior.
- PNG output uses the adapter's `max_size=2048` render limit and can therefore be downscaled for large canvases. Structural validation remains in source pixel coordinates.

### Typography

The external schema has no public line-map field. The project adapter creates the upstream renderer's internal line map from unchanged JSON text:

- Existing newline characters are hard breaks. Width-based breaks are deterministic adapter behavior, not `cr-renderer` behavior; a break may replace an existing space in the transient render representation, but the JSON `content` is never changed.
- The adapter MUST treat UAX #29 extended grapheme clusters as atomic units and use UAX #14 line-break opportunities intersected with those cluster boundaries. It MUST use a latest-fitting greedy break, count every visual line including forced empty lines, and reject an unbreakable segment that cannot fit. It MUST NOT hyphenate, rewrite, reorder, delete, or silently truncate content.
- External style-run ranges are 0-based, end-exclusive (`[start, end)`) code-point ranges. They MUST satisfy `0 <= start <= end <= len(content)`; empty ranges are no-ops, and later overlapping runs win per property supplied. A style boundary inside a grapheme cluster may affect metrics but is not itself a break opportunity. The adapter converts valid external ranges to the upstream renderer's inclusive internal ranges only at the transient line-map boundary.
- The adapter MUST measure the effective loaded font and style-run face, serialized integer renderer font size, span-local letter spacing, and the transient line map actually supplied to the renderer. It MUST enforce `max_lines` and line-box height, validate actual positioned glyph bounds, and reject overflow rather than truncate or silently clip. Alignment remains left, center, or right within the element width.
- Upstream line origins advance by `line_index * font_size * line_height`; glyph advances include letter spacing. The check includes forced empty lines and occurs after final integer serialization.
- When `stroke_color` and positive `stroke_width` are present, the adapter MUST rasterize rectangle and ellipse strokes inside their declared boxes without expanding public geometry or creating pixels outside those boxes. The source fields remain unchanged.

The adapter implements the renderer-conformance rules above. Renderer golden comparisons, native-library parity, and native-amd64 qualification remain evidence gates; they do not weaken the contract.

### Images, shapes, and missing assets

- A source image with `fit=contain` is isotropically resized and letterboxed; `cover` is isotropically resized and center-cropped; `fill` is stretched to the element box by the project adapter before the upstream renderer draws it.
- Only a classified full-canvas background may use target-shape cover cropping. Foreground JSON box ratios remain source-invariant even when `fit=fill` or `fit=cover`.
- Shapes are rasterized by the project adapter because `cr-renderer` has no native shape primitive. The pinned adapter renders rectangles, rounded rectangles, ellipses, and horizontal lines, including declared rectangle/ellipse strokes inside their boxes; renderer golden and platform qualification remain pending evidence.
- A missing asset keeps its original `asset_id` and element record. The renderer MAY emit the deterministic labeled placeholder used by `assets.py` for a diagnostic PNG and MUST emit a warning. The engine never writes the placeholder into the response JSON or treats it as a replacement asset.
- Renderer import failure is a `RUNTIME_IO_FAILURE`; the engine MUST publish no JSON/PNG pair. Missing-asset placeholders remain permitted only as diagnostic render output after a successful adapter import.

## 7. Geometry, grouping, and image invariants

For an element center `(cx, cy)`, width `w`, height `h`, and fixed rotation `theta` in degrees, the rotated axis-aligned envelope is:

```text
a = |w cos(theta)| + |h sin(theta)|
b = |w sin(theta)| + |h cos(theta)|
AABB = [cx-a/2, cx+a/2] x [cy-b/2, cy+b/2]
```

All trigonometric calculations use degrees converted to radians. Contract ratio feasibility and equality comparisons remain exact; the pinned runtime's trigonometric path MAY be used for rotated-envelope calculation without intermediate rounding. The validator applies the formula after integer serialization.

### Background and intentional bleed

A background is an image with `fit="cover"` whose source rotated envelope covers the entire source canvas. If multiple images qualify, choose the lowest effective `z_index`, then the largest source rotated-envelope area, then source array order. If no image meets the rule, there is no background exemption.

The only off-canvas foreground exception in Stage 1 is a **source-bleed decoration**: an ungrouped `shape` with `opacity < 1` whose source rotated envelope intersects the source canvas but extends outside it. Such a record MUST remain visible in the target, retain the same clipped side set, still intersect the target canvas, and never disappear completely. It may remain clipped. This narrow rule covers the Level 2 corner decoration; arbitrary off-canvas content is not exempt.

Every other active foreground element MUST have its rotated AABB inside the target canvas. Backgrounds may cover the target through the renderer's `cover` preprocessing.

### Images

For every positive-area foreground image:

```text
output.width * source.height == output.height * source.width
```

The comparison is made on serialized geometry. For a positive-area source ratio reduced to positive integers `p/q`, a valid positive-area foreground image output uses integer multiples `(k*p, k*q)` for a positive integer `k`; if no such hard-valid geometry exists, the candidate is rejected rather than repaired by ratio drift. Source-degenerate image records remain records without a ratio calculation. Backgrounds are exempt from this box-ratio rule because they are allowed to cover the target.

### Groups and overlap

- Equal non-null `group_id` values define rigid units. A group's children receive one common scale `s > 0` and translation `t`: `child_center' = s * child_center + t`, `child_width' = s * child_width`, and `child_height' = s * child_height`. Children inherit that transform; no child may drift independently. Text `font_size` may change only inside the transformed child box and may not alter the group transform or move a sibling.
- For ungrouped records, containment and proximity are layout hints only. Overlap alone does not create a group.
- For active positive-area records, two rotated AABBs collide only when their intersection has positive area. Edge or point boundary contact is allowed. Source-overlapping pairs may remain overlapped; pairs whose rotated source envelopes were separate MUST remain separate in every hard-valid candidate, except when the target is declared infeasible. A zero-area record does not create a positive-area collision by itself. Text over a busy image is separately checked against the rendered pixels below it.
- Source-intended overlap, identity, and fixed-property checks occur before soft aesthetic scoring.

## 8. Hard constraints, soft objectives, and infeasible targets

A candidate is hard-valid only if all of these pass:

1. Valid request/response structure and exact target canvas.
2. Same unique IDs, count, order, types, and immutable fields.
3. Finite serialized geometry; no newly hidden, opacity-zero, removed, replaced, or intentionally zero-sized records.
4. Rotated containment, with only the background and source-bleed exceptions above.
5. Foreground image box-ratio invariance.
6. Rigid group relationships and no new collision between source-separated pairs.
7. Text content/style preservation and actual glyph bounds inside the text geometry.
8. No engine-generated or replaced asset pixels.

These are ranking preferences after hard validation: readable font size (roughly 10 px unless the source is smaller), contrast against the actual rendered pixels, source hierarchy, alignment, even spacing, visual balance, whitespace, and preservation of ungrouped source overlap area. A proxy score MUST NOT rescue a hard-invalid candidate.

The infeasible-layout fallback is **fail closed**. If candidate generation cannot produce a hard-valid result, `resize()` MUST raise a typed `InfeasibleLayoutError` (or the language-equivalent error with a reason code), and the batch runner MUST write no Stage 1 design/PNG for that task and return a nonzero status. It MUST NOT return a misleading best-effort design. Relaxing soft objectives is allowed; relaxing a hard rule, shedding an element, changing copy/font attributes, or using zero size/opacity is not.

The accepted internal task statuses are `SUCCESS`, `MALFORMED_INPUT`, `INFEASIBLE_LAYOUT`, `INCOMPLETE_SEARCH`, and `RUNTIME_IO_FAILURE`. A success commits the design JSON and PNG as one logical pair; every failed task publishes neither artifact, and no failure JSON envelope or best-effort design is added to the wire contract. The runner stages and validates both artifacts before pair publication, removes or quarantines stale paths on failure, may continue independent tasks, and returns a nonzero aggregate status if any task fails or does not commit both artifacts.

A hard-valid candidate found before an optimization cutoff MUST be returned after serialized hard validation. A cutoff without a hard-valid candidate is `INCOMPLETE_SEARCH`, never proven infeasibility. Only an exhausted finite search with no hard-valid candidate is `INFEASIBLE_LAYOUT`.

To prevent avoidable task failure in automated scoring, candidate generation MUST actively maximize feasibility on extreme canvas aspect ratios by applying all contract-permitted geometric levers before declaring infeasibility: reducing font sizes to the readable floor (10px–12px), scaling foreground artwork isotropically down to recognizable minimums, switching to horizontal ribbon or column-pivot topologies, and compressing margins. `INFEASIBLE_LAYOUT` is reserved strictly for mathematically unsolvable layouts or invalid/degenerate dimensions.

Target generation should avoid infeasible pairs, but hidden inputs remain entitled to the same deterministic failure protocol.

## 9. Stage 1 runtime target

- The official artifact is a single-platform `linux/amd64` container running Python 3.11.
- Runtime network access is disabled with `docker run --network none`. All dependencies, renderer code, fonts, brand assets, and any future model weights are present before task processing.
- The initial dependency baseline is pinned in `chameleon/requirements.txt`; the base image is pinned in `chameleon/Dockerfile`. Build-time network access is allowed, but a future release needs a hash-locked wheelhouse for fully reproducible offline builds.
- Apple Silicon development must use Buildx with `--platform linux/amd64` or native amd64 CI. An arm64-only local pass is not Stage 1 evidence; emulation can be slower.
- Hardware budget and execution profile: The scoring environment runs linux/amd64 containers on an Apple M5 Pro host under Rosetta 2 emulation without host GPU passthrough. The engine must operate CPU-only, budget for <= 8 CPU threads, stay under 8 GB RAM, and maintain a total Docker image size under 8 GB.
- Dynamic asset and font resolution: All fonts and artwork must be loaded dynamically from `brand_kit/fonts` and `brand_kit/assets` based on task JSON references. Asset filenames and font families must never be hardcoded.
- Performance targets: The engine operates with a 0 MB neural weight footprint (100% deterministic symbolic solver), targeting < 2.0s CPU latency per design under x86 emulation, < 500 MB resident solver RAM, and bit-identical reproducibility across runs.
- There is no hard Stage 1 latency disqualifier in the supplied challenge rules. The exact M5 Pro CPU/RAM/disk/GPU budget and model allowlist remain organizer-controlled TBD facts and are not invented here.
- OR-Tools CP-SAT is not a current dependency or contract requirement. If selected later, it needs a separate pinned dependency decision and integer-model conformance test.
- The initial search strategy is deterministic structured search: multi-signal role inference; four topology families (near-isomorphic, column pivot, horizontal ribbon, and vertical re-stack); at most three source-derived slot/emphasis variants per family; renderer-in-loop hard validation; fixed-point ranking; and stable tie-breaks. No model or OR-Tools dependency is used initially. A later solver or model requires held-out gain and a separate accepted ADR; it MUST NOT weaken hard validation.

## 10. Stage 1 versus finale

Stage 1 is autonomous and identity-preserving. It does not expose user pinning, candidate selection, element shedding, copy revision, font substitution, or a reduced preview. Image regeneration, redrawing, replacement, inpainting, seam carving, and outpainting are prohibited in every stage.

The finale may wrap the engine in an Adobe Express add-on and may explore user-approved pinning, candidate selection, copy alternatives, font substitution, or a reduced composition as separate interactions. A finale preview that changes records or copy is never labeled a Stage 1 output. For the live showcase at Adobe HQ, the Express add-on (running in an iframe via `@adobe/express-add-on-sdk`) connects to the Stage 1 engine exposed as a lightweight local HTTP service (e.g. FastAPI/Flask on localhost) or WebAssembly module. Adobe Express API facts are evidence for future work, not Stage 1 dependencies.

## 11. Requirement traceability

| Requirement | Contract/ADR | Structural or semantic rule | Conformance evidence | Implementation status |
| --- | --- | --- | --- | --- |
| Authority hierarchy | ADR-001 | This document's precedence list | `PROJECT_CONTRACT.md` §2 | Ratified |
| Exact mutable fields and identity | ADR-002 | §5 plus schema required fields | `tests/contract/test_contract.py`, `tests/geometry/`, runner publication cases | Structural validator and bounded solvers implemented; platform qualification remains separate |
| Empty designs and source degenerates | ADR-003 | Schema `elements.minItems=0`; no new zero-size records | `tests/contract/`, `tests/layout/`, runner cases | Implemented locally; broader catalogue evidence remains pending |
| Rotated containment and bleed | ADR-003 | §7 AABB and source-bleed predicate | `tests/geometry/`, `tests/layout/` | Implemented locally; renderer/platform qualification remains separate |
| Foreground image ratios | ADR-003 | Cross-product equality after rounding | `tests/geometry/`, `tests/layout/` | Implemented locally with post-serialization validation |
| Renderer/text semantics | ADR-002 | §6 and pinned source revision | `tests/contract/test_renderer_contract.py`, `tests/renderer/`, renderer preflight and artifact seams | Authoritative contract seam and bounded adapter evidence implemented; native/platform goldens remain unverified |
| Infeasible target behavior | ADR-003 | Typed failure, no misleading output | `tests/layout/`, `tests/runner/test_runner.py` | Bounded exhaustion/cutoff mapping and fail-closed publication implemented |
| Offline runtime and platform | ADR-004 | Docker/request pins and network rule | Docker/buildx smoke plan in `STATUS.md` | Local/CI evidence is recorded; native-amd64 and clean-cache qualification remain unverified |
| Stage split | ADR-005 | §10 | Stage boundary review | Ratified |
| Failure protocol and search status | ADR-006 | Typed internal statuses; no failure envelope; no failed-task artifacts; logical JSON/PNG pair publication; conservative cutoff semantics; nonzero aggregate failure | `tests/runner/test_runner.py`, `tests/layout/test_search_ranking.py` | Runner staging, cleanup, aggregate exit, and bounded cutoff/exhaustion semantics implemented |
| Numeric and geometry semantics | ADR-007 | Exact rational ingress; one half-even serialization; reduced image-ratio lattice; rigid group transform; AABB and positive-area overlap rules | `tests/geometry/`, `tests/layout/`, runner exact-ingress cases | Implemented locally with final serialized validation |
| Typography and renderer edge semantics | ADR-008 | Grapheme-safe UAX #14/UAX #29 wrapping; style-run semantics; effective span metrics; overflow rejection; in-box strokes; no public line map | `tests/renderer/`, renderer preflight, artifact corpus | Bounded adapter and local evidence implemented; final fonts/native parity remain unverified |
| Initial deterministic search | ADR-009 | Four topology families, bounded source-derived variants, renderer-in-loop validation, fixed-point ranking, no model/CP-SAT initially | `chameleon/tests/layout/test_issue23_search_evidence.py`, `test_search_ranking.py`, `test_heldout_evaluation.py`, `Docs/IMPLEMENTATION/tickets/08-heldout-evaluation.md` | Bounded search and local held-out-style evidence implemented; official/native qualification pending |

The source-driven verification record and external URLs are in [DEPENDENCY_EVIDENCE.md](DEPENDENCY_EVIDENCE.md). Current implementation gaps are tracked in [STATUS.md](STATUS.md).
