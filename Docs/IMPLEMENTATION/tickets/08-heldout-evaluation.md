# Ticket 08 held-out search evaluation

This record closes the implementation gap for a **local, checked-in held-out-style
corpus evaluator**. It does not turn the corpus into an official qualification
set. `Docs/PROJECT_CONTRACT.md` §§5–9, Accepted ADR-001 through ADR-013 (in
particular ADR-006, ADR-007, and ADR-009 through ADR-013), the pinned
renderer/dependency records, and the `chameleon-contract`, `chameleon-testing`,
and `chameleon-review` skills remain authoritative.

## Corpus provenance and coverage matrix

`chameleon/tests/fixtures/heldout_search_cases_v1.json` preserves the original
five locally authored source/target pairs. The evaluator-only metadata added to
that versioned fixture does not alter source or target documents.
`chameleon/tests/fixtures/heldout_search_cases.json` is corpus v2: it preserves
the v1 pairs and adds two contract interaction cases. None references a public
file in `chameleon/input/`.
`expected_status`, optional `expected_reason_code`, and `coverage` are
evaluator-only metadata; they are not source design fields. The source and
target documents are validated against the ratified Draft 2020-12 schema, and
search runs through the pinned local renderer and serialized hard validator.

The dimensions below come from the schema and the accepted hard contract.
Coverage labels are stored per case in the fixture and copied to each report
entry so the authored scope can be checked alongside observed outcomes.

| Contract dimension | Corpus case and concrete shape | Boundary measured |
| --- | --- | --- |
| Canvas aspect ratios (schema `canvas`; contract §8; ADR-009 §3) | `horizontal-ribbon-journal` target 800×200 (4:1), `vertical-restack-studio` target 200×1600 (1:8), and `extreme-ratio-incomplete` target 728×90 | Both successful extreme topologies and one explicit typed `INCOMPLETE_SEARCH`; the latter is not called infeasible and emits no selected candidate signature. |
| Rigid groups and source-intended overlap (schema `group_id`; contract §7; ADR-007 §§4, 7) | `contract-interactions`: `group_panel` and `group_label` share `quiet-cta` and positively overlap in the source | The selected hard-valid response preserves their common scale/translation; the label-over-panel overlap is intentional, not a new collision. |
| Rotated bounds (schema `rotation`; contract §7; ADR-007 §3) | `contract-interactions`: foreground `gallery_vessel` has 11° rotation | Renderer-gated admission recomputes the rotated AABB after integer serialization. |
| Foreground image ratios (schema image `width`/`height`/`fit`; contract §7; ADR-007 §2) | Existing product images plus `contract-interactions` `gallery_vessel` (600×580 source box) | Hard validation checks the exact serialized cross-product ratio; background cover treatment is separate. |
| Text wrapping, style runs, and glyph edges (schema text/style fields; contract §6; ADR-008 §§1–4) | `contract-interactions` has a long italic title, `max_lines=2`, negative letter spacing, and a color style run; `group_label` is a separate grouped text child | Actual adapter wrapping, effective face/spacing, style-run range, and positioned glyph-bound checks run before candidate admission; text/copy fields stay fixed. |
| Background and source bleed (schema image `fit` and shape `opacity`; contract §7; ADR-007 §§5–6) | `contract-interactions` has a full-canvas `solstice_bg_gradient.png` `fit=cover` background and a translucent ellipse clipped on the source's left side | Background exemption uses the contract predicate; the ellipse remains visible and clipped on the same side. |
| Missing-asset preservation (schema image `asset_id`; contract §6) | `missing-asset-diagnostic` references `heldout_asset_not_packaged.png` | Successful diagnostics retain the original element and asset ID; the renderer warning/placeholder is not written into the design response. |

The corpus keeps the four topology-focused cases and the missing-asset case from
v1. Fixture labels describe the authored shape, not official target catalog
coverage or organizer-held-out qualification.

The evaluator loads JSON with `parse_int=int`, `parse_float=Decimal`, and
non-finite-number rejection. It invokes `engine.layout.search.search` directly,
with the checked-in assets and fonts, and does not call or alter the public
response returned by `resize()`.

## Historical v1 five-case observation

The exact offline command is:

```bash
cd chameleon
../.venv/bin/python ../scripts/evaluate_heldout_search.py \
  --corpus tests/fixtures/heldout_search_cases_v1.json \
  --repeats 2 \
  --output /tmp/chameleon-heldout-search-v1.json
```

The command keeps v1 inputs separate from v2 additions. The current evaluator
emits expanded v2 evidence fields; metrics and report hash below are archival
observations from the v1 evaluator format.

Observed on the local Darwin arm64 workstation:

- Five authored cases ran twice each; all ten response/PNG signatures were
  byte-stable. Every case returned `SUCCESS`; no candidate-work cutoff occurred.
- The evaluator considered all four topology families in every 12-item work
  set. Admitted topology coverage was `near_isomorphic` (all cases),
  `column_pivot` (the column and horizontal cases), `horizontal_ribbon`
  (the horizontal case), and `vertical_restack` (the vertical case).
- 27 of 60 evaluated work items were hard-valid (`hard_valid_rate=0.45`).
  The selected-topology distribution was `near_isomorphic=3` and
  `column_pivot=2`; fixed-point quality remains separate soft evidence. On a
  native Linux aarch64 container the `vertical-restack-studio` case selected
  `vertical_restack` instead (`near_isomorphic=2`, `column_pivot=2`,
  `vertical_restack=1`) while hard admission (3, 6, 9, 6, and 3 admitted
  candidates, same families) matched, so selection is platform dependent and
  hard admission is the portable evidence.
- The observed failure-reason distribution contains 33
  `INCOMPLETE_SEARCH` rejected family/variant attempts; no admitted candidate
  had a serialized validation error. The missing-asset case emitted the
  authorized deterministic placeholder warning twice, while preserving the
  source asset reference.
- Per-case runtime ranged from 2512.9 ms to 15081.7 ms across the two
  repeats. Process maximum RSS ranged from about 222 MiB to 225 MiB on this
  host; this is not container or native-amd64 qualification.
- The captured report SHA-256 was
  `68d7e611ef85047998cbf9105a6b71c60084390608a982d4ffe51744589faa47`.
  This is not a determinism pin: runtime and RSS fields are intentionally
  observed evidence and vary between runs. Determinism is asserted on the
  response/PNG signatures and on the persisted engine artifact fixture.

No result is inferred from fixture construction or from soft quality scores.

## Expanded v2 observation

The v2 corpus and evaluator implement the expanded local evidence requested
for the search-corpus gap. This run used the offline local renderer on the
Darwin arm64 workstation; it is not native-amd64, organizer-held-out, or
official qualification evidence.

Exact command:

```bash
cd chameleon
../.venv/bin/python ../scripts/evaluate_heldout_search.py \
  --corpus tests/fixtures/heldout_search_cases.json \
  --repeats 2 \
  --output /tmp/chameleon-heldout-search.json
```

All seven authored expected task outcomes matched: six `SUCCESS` and one
`INCOMPLETE_SEARCH`. All seven task outcomes were stable across repeats; all
six successful cases had stable canonical-response and PNG signatures. The
failed case has no selected candidate or response/PNG signature. All source
documents remained unchanged, and no candidate produced a serialized hard
validation error. The `contract-interactions` title was observed wrapping to
two lines in the pinned converter output.

| Case | Expected → observed status / task reason | Hard-valid admissions / evaluated | Candidate rejection reason codes | Selected topology | Repeat task / response / PNG |
| --- | --- | ---: | --- | --- | --- |
| `isomorphic-gallery` | `SUCCESS` → `SUCCESS` / — | 3 / 12 | `INCOMPLETE_SEARCH` ×9 | `near_isomorphic` | stable / stable / stable |
| `column-pivot-catalog` | `SUCCESS` → `SUCCESS` / — | 6 / 12 | `INCOMPLETE_SEARCH` ×6 | `near_isomorphic` | stable / stable / stable |
| `horizontal-ribbon-journal` | `SUCCESS` → `SUCCESS` / — | 7 / 12 | `INCOMPLETE_SEARCH` ×3; `SOURCE_SEPARATION_VIOLATION` ×2 | `column_pivot` | stable / stable / stable |
| `vertical-restack-studio` | `SUCCESS` → `SUCCESS` / — | 5 / 12 | `INCOMPLETE_SEARCH` ×6; `SOURCE_SEPARATION_VIOLATION` ×1 | `near_isomorphic` | stable / stable / stable |
| `missing-asset-diagnostic` | `SUCCESS` → `SUCCESS` / — | 2 / 12 | `INCOMPLETE_SEARCH` ×9; `SOURCE_SEPARATION_VIOLATION` ×1 | `near_isomorphic` | stable / stable / stable |
| `contract-interactions` | `SUCCESS` → `SUCCESS` / — | 1 / 12 | `INCOMPLETE_SEARCH` ×9; `SOURCE_SEPARATION_VIOLATION` ×2 | `near_isomorphic` | stable / stable / stable |
| `extreme-ratio-incomplete` | `INCOMPLETE_SEARCH` → `INCOMPLETE_SEARCH` / `INCOMPLETE_SEARCH` | 0 / 8 | `INCOMPLETE_SEARCH` ×8 | none | stable / n/a / n/a |

Each case considered the four bounded topology families. Across the seven
cases, 24 of 80 evaluated candidate work items were admitted as hard-valid
(`hard_valid_rate=0.30`); candidate rejection reasons were
`INCOMPLETE_SEARCH` ×50 and `SOURCE_SEPARATION_VIOLATION` ×6. The separate
task-level reason distribution contains one `INCOMPLETE_SEARCH`. No work-set
cutoff was reported, but finite search was not exhausted; therefore the
extreme-ratio result remains `INCOMPLETE_SEARCH`, not infeasibility. The
selected-topology distribution was `near_isomorphic` ×5 and `column_pivot` ×1;
no topology is selected for the failed case.

These v2 counts are separate from the five-case 27/60 versus 24/60 admission
discrepancy tracked by issue #62; the v2 denominator includes two added cases.
This report does not reconcile that baseline discrepancy or tune search
toward 0.45.

The evaluator JSON captured for this run had SHA-256
`9bdc5da880c390014cbfdcf6139846ce4274e9e4b6a1332f789169e20a2e71f2`; the
fixture SHA-256 was
`1659bdf4f99b226a26285906d7aee2ab36e7cce73b7bb2f5b26c7bc03cd02e75`.
Response signatures are SHA-256 over the evaluator's sorted canonical response
mapping (including exact-decimal markers); PNG signatures hash rendered bytes.
The report also records per-case fixed-point soft-quality components and
wall-time/process-RSS observations separately. On this host the observed
per-run wall time ranged from 1.7 to 1280.7 ms and reported process maximum
RSS from 249,610,240 to 324,452,352 bytes. These are local observations, not
resource qualification or ranking claims. Runtime and RSS values are
measurements and are not determinism pins.

No result is inferred from fixture construction or from soft quality scores.

## Evidence separation

The v2 report keeps measured task outcomes in `hard_evidence`, fixed-point
ranking metrics in `soft_quality`, wall time and process RSS in
`runtime_observations`, and authored expected-status checks in
`outcome_expectations`.

Per-case hard evidence includes:

- actual task status and its task-level reason code, separate from the
  distribution of rejected candidate reason codes;
- candidate count, evaluated/admitted counts, hard-valid admissions, cutoff,
  and finite-work-exhaustion state;
- topology work-set coverage, hard-admitted topology coverage, and the selected
  topology as a separate field;
- a canonical response SHA-256 and PNG SHA-256 for the selected candidate,
  with separate repeated response-signature and PNG-signature stability flags;
- independent serialized `validate_response(source, target_canvas, response)`
  results and source immutability; and
- deterministic repeated task outcome/signature state.

Failed search cases have no selected response/PNG signature and no soft-quality
candidate. Their reason codes remain typed. An `INCOMPLETE_SEARCH` outcome is
not promoted to `INFEASIBLE_LAYOUT`; the evaluator itself does not publish task
artifacts. Runner publication/failure behavior remains covered at its separate
runner tests.

Soft evidence records fixed-point `QualityScore` components only for admitted
candidates. Runtime observations are not hard validity or scorer evidence.
`test_heldout_evaluation.py` checks every source/target against the schema,
the coverage matrix and expected task class, every admitted success response
through the hard validator, candidate-level rejection accounting, all four
admitted topology families, the explicit incomplete-search case, and stable
response/PNG signatures separately. It does not pin incidental quality scores
or claim organizer-controlled performance.

## Limits and disposition

This is evidence from the local corpus and pinned offline renderer only. It is
not an official held-out benchmark, organizer-controlled evaluation, or native
amd64 qualification. The local workstation is arm64; no native-amd64 result is
claimed. Process RSS is host-process evidence when available, not a container
memory measurement. Clean-cache behavior, organizer-controlled resource
limits, external hidden cases, and cross-platform PNG parity remain outside
this record. Missing-asset behavior is recorded as the actual typed status or
renderer warning observed by the evaluator rather than being converted into a
pass claim.
