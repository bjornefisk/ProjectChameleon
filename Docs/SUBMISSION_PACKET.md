# Project Chameleon submission packet

## Purpose

Use this file as the final review checklist. It explains the project in plain language, records evidence already collected, and separates open checks from completed work.

## Project in one minute

Project Chameleon resizes a design from one canvas to another. It keeps every source item, its text, its image, its order, and its link to the source. It changes only the canvas, item position and size, and text size.

The program tries a small, fixed set of layout patterns. It measures each draft with the project renderer, keeps only drafts that pass every required check, and selects the best passing draft with a repeatable score. If no draft passes, it writes no design output.

## Current implementation state

- Gate 1 is complete. The drawing tool and rule checker passed their required local checks.
- Work items 01 through 08 are implemented within accepted limits.
- The public Level 3 case, `1080x1350 -> 728x90`, produced a valid JSON and PNG pair in repeated local runs.
- Issue #61 public Level 3 work merged in PR #65 at commit `6dbbc0a3eaba3090997ad9731a4026677dc6978c`.
- The required native `x86_64` verification run `39711973748` passed on PR head `33f6fd9`.
- Reproducible package locks merged in PR #80. Native run `40233682826` passed.
- Issue #81 covered 18 local synthetic cases. This is local evidence only.
- No official organizer score is recorded.
- Cross-platform matching, tests on hidden organizer examples, and release checks remain unverified.
- Partner review was waived by the repository owner. No partner approval is recorded.

## Rules the final package must preserve

1. Keep every source record, identifier, count, order, type, fixed field, text, image, and source link.
2. Change only the target canvas, item position and size, and text size.
3. Store changed numbers as finite integers.
4. Keep image width-to-height ratios exact.
5. Keep grouped items together with one shared scale and move.
6. Check turned item edges, overlap between source groups, and rendered text bounds.
7. Keep missing image references instead of removing them.
8. Use the four approved layout patterns and the fixed draft limit.
9. Keep the program offline at run time.
10. Do not add models, CP-SAT, OR-Tools, or another unapproved solver.
11. Stop safely when no valid draft exists. Do not publish a partial design.

## Final review checklist

### Files and claims

- [ ] Read `Docs/PROJECT_CONTRACT.md` and every accepted ADR.
- [ ] Read `Docs/STATUS.md` for current evidence and open boundaries.
- [ ] Confirm README links point to current documents.
- [ ] Remove draft wording from submission-facing material.
- [ ] Label local evidence as local evidence.
- [ ] Label organizer-controlled facts as unverified until checked.
- [ ] Add the project PDF supplied by the team before final upload.

### Commands

Run the recorded integration sequence from a native `linux/amd64` environment:

```bash
cd chameleon
python -m engine.main
python -m unittest discover -s tests -p 'test_*.py' -v
docker buildx build --platform linux/amd64 --load -t chameleon-stage1 .
docker run --rm --network none \
  -v "$PWD/input:/app/input" -v "$PWD/output:/app/output" \
  chameleon-stage1
```

Record each exit result, output file, and deterministic failure result. Keep required checks separate from visual quality notes.

### Output review

- [ ] Confirm output contains one JSON design and one PNG preview when the run succeeds.
- [ ] Confirm JSON keeps all source records and source links.
- [ ] Confirm changed values are finite integers.
- [ ] Confirm image ratios and group relationships remain valid.
- [ ] Confirm rendered text and rotated bounds pass validation.
- [ ] Confirm missing image references remain present.
- [ ] Confirm no output appears after a failed run.

## Missing project PDF

No project or challenge PDF is present in this checkout. No authoritative source link is recorded here. Do not create a substitute and label it as the supplied PDF. Add the original file or its authoritative source before final packaging.

Until that file arrives, this packet and `Docs/PRESENTATION.md` are the usable written guidance. They do not replace the requested source PDF.

## Evidence map

- Contract and accepted decisions: `Docs/PROJECT_CONTRACT.md`, `Docs/DECISIONS/`, and `Docs/DECISION_REGISTER.md`
- Current status and evidence: `Docs/STATUS.md`
- Architecture boundary: `Docs/FINAL_ARCHITECTURE.md`
- Dependency and package evidence: `Docs/DEPENDENCY_EVIDENCE.md`
- Presentation outline: `Docs/PRESENTATION.md`
- Public Level 3 evidence: `Docs/STATUS.md` and `Docs/DEPENDENCY_EVIDENCE.md`

## Final claim boundary

Claim only what local files, recorded commands, and recorded runs prove. Treat organizer scoring, the final target list, production font availability, native library availability, and deployment details as open until an authoritative source confirms them.
