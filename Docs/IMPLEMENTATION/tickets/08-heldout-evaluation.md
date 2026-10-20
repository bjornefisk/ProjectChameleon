# Ticket 08 held-out search evaluation

This record closes the implementation gap for a **local, checked-in held-out-style
corpus evaluator**. It does not turn the corpus into an official qualification
set. `Docs/PROJECT_CONTRACT.md` §§5–9, Accepted ADR-001 through ADR-009 (in
particular ADR-006, ADR-007, and ADR-009), the pinned renderer/dependency
records, and the `chameleon-contract`, `chameleon-testing`, and
`chameleon-review` skills remain authoritative.

## Corpus provenance and scope

`chameleon/tests/fixtures/heldout_search_cases.json` contains five source/target
pairs authored specifically for this corpus. They do not reference or derive
from the public files in `chameleon/input/`:

- `isomorphic-gallery` exercises the near-isomorphic route;
- `column-pivot-catalog` supplies a wide target for column-pivot routing;
- `horizontal-ribbon-journal` supplies a compressed wide target for the
  horizontal-ribbon route;
- `vertical-restack-studio` supplies a tall narrow target for vertical-restack
  routing; and
- `missing-asset-diagnostic` keeps a deliberately unavailable asset in the
  corpus so renderer diagnostics and the fail-closed boundary remain observable
  when the local renderer permits a warning-backed result.

The evaluator loads JSON with `parse_int=int`, `parse_float=Decimal`, and
non-finite-number rejection. It invokes `engine.layout.search.search` directly,
with the checked-in assets and fonts, and does not call or alter the public
response returned by `resize()`.

## Exact command and observed result

The exact offline command is:

```bash
cd chameleon
../.venv/bin/python ../scripts/evaluate_heldout_search.py \
  --corpus tests/fixtures/heldout_search_cases.json \
  --repeats 2 \
  --output /tmp/chameleon-heldout-search.json
```

Observed on the local Darwin arm64 workstation:

- Five authored cases ran twice each; all ten response/PNG signatures were
  byte-stable. Every case returned `SUCCESS`; no candidate-work cutoff occurred.
- The evaluator considered all four topology families in every 12-item work
  set. Admitted topology coverage was `near_isomorphic` (all cases),
  `column_pivot` (the column and horizontal cases), `horizontal_ribbon`
  (the horizontal case), and `vertical_restack` (the vertical case).
- 27 of 60 evaluated work items were hard-valid (`hard_valid_rate=0.45`).
  The selected-topology distribution was `near_isomorphic=3` and
  `column_pivot=2`; fixed-point quality remains separate soft evidence.
- The observed failure-reason distribution contains 33
  `INCOMPLETE_SEARCH` rejected family/variant attempts; no admitted candidate
  had a serialized validation error. The missing-asset case emitted the
  authorized deterministic placeholder warning twice, while preserving the
  source asset reference.
- Per-case runtime ranged from 236.9 ms to 1045.2 ms across the two repeats.
  Process maximum RSS ranged from about 224 MiB to 278 MiB on this host; this
  is not container or native-amd64 qualification.
- Report SHA-256:
  `7727f6245eb050f74d9cedfd3bf376fed93936f59804e3ab3070a445b48f8976`

No result is inferred from fixture construction or from soft quality scores.

## Evidence separation

The report has separate `hard_evidence` and `soft_quality` sections.

Hard evidence includes, for every admitted candidate and selected response:

- serialized `validate_response(source, target_canvas, response)` success;
- response immutability of the caller-owned source;
- status and reason-code distributions, including typed failures;
- candidate count, evaluated/admitted counts, cutoff flags, and hard-valid rate;
- topology work-set coverage, admitted topology coverage, and selected
  topology distribution;
- exact response signatures and SHA-256 hashes/lengths of PNG bytes;
- repeated-run signature and PNG-byte stability;
- wall runtime and process maximum RSS when the platform exposes it.

Soft evidence records the fixed-point `QualityScore` components and selected
candidate components only after hard validation. Quality values do not rescue a
hard-invalid candidate, establish topology validity, or establish qualification.
The permanent regression test asserts required metric shapes, hard validation,
repeat determinism, the twelve-candidate bound, and all-four-family work-set
coverage; it intentionally does not assert incidental score values.

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
