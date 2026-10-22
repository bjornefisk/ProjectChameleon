# ADR-011: Treat readable font size as a renderer-validated preference

## Status

Accepted — the issue owner authorized this PDF-grounded decision and an independent reviewer returned APPROVE on 2026-10-21. Repository maintainer review of the implementation PR remains required before merge.

## Date / owner / reviewers

- Date: 2026-10-21
- Owner: @bjornefisk (issue owner/project authority)
- Reviewers: independent reviewer role (ADR proposal review, APPROVE, 2026-10-21); partner review on implementation PR #65 was waived by repository owner @bjornefisk before merge; no partner approval is recorded.

## Context / authority

The original challenge PDF §2.5 requires text to be readable but defines no numeric minimum. Section 7.2 says changing font size is expected and treats text content and font family as fixed. The project contract §8 ranks readable size “roughly 10 px unless the source is smaller,” but its §8 extreme-ratio paragraph and ADR-006 §3b describe a 10–12px “readable floor.” The latter phrase is a project-authored numeric constraint, not a value supplied by the organizer, and it conflicts with the explicit ranking-preference treatment.

The public Level 3 728×90 sample cannot fit all required text and groups with the project-authored 10px floor. The PDF requires legibility, not a particular font-size number. Size alone does not establish readability; the pinned renderer's line wrapping, actual glyph bounds, contrast, and the rendered artifact remain relevant.

## Decision

There is no universal numeric Stage 1 readability floor derived from the challenge PDF. A font size around 10px remains a ranking preference, not a hard minimum. A smaller positive integer font size MAY be considered only when:

1. source text and every fixed typography field remain unchanged;
2. the candidate passes the pinned renderer's line-count, line-box, width, actual glyph-bound, and artifact hard checks after serialization;
3. the complete rendered result is independently inspected to assess local legibility and contrast; this is recorded as soft-quality evidence, not a hard metric or proof of official scorer acceptance; and
4. ranking continues to prefer a larger readable size when otherwise comparable.

This decision does not make unreadable output acceptable. If the rendered candidate fails the PDF's qualitative readability requirement, issue #61 is not complete and must not be closed. Local visual review does not establish organizer scoring or qualification. This decision does not authorize copy edits, font substitution, line-height changes, text clipping, or a new schema/API field.

## Options considered

1. Keep 10px as a hard minimum. Rejected: the supplied PDF does not state it, and it prevents use of the explicitly expected font-size adaptation on this extreme target.
2. Remove all readability checks. Rejected: §2.5 explicitly requires readable text and the output PNG is scored.
3. Keep ~10px as a soft preference, validate actual renderer bounds, and require visual legibility evidence for the issue's sample. Selected.

## Consequences / tradeoffs

- Search may consider integer sizes below 10 only after larger sizes fail the candidate's real geometry; ranking still values larger legible sizes.
- A hard-valid font box is not, by itself, evidence that its copy is visually readable. Hard and soft evidence remain separate.
- Issue #61's previous area certificate is conditional on a project-authored 10px floor and cannot be used as an organizer-backed proof of infeasibility.

## Security / dependency / data impact

No dependency, schema, runtime, network, source data, asset, or public API change. Existing local fonts and pinned renderer remain authoritative.

## Migration / rollback

Update the normative contract and ADR-006's feasibility wording in the same cutover. Keep the current fail-closed behavior for any candidate that fails hard renderer checks or visual readability. If visual inspection finds the public result unreadable, do not claim success or close issue #61; seek project-owner/organizer direction rather than further lowering text size or changing copy/family.

## Affected files / callers / docs

`Docs/PROJECT_CONTRACT.md` §8; ADR-006 §3b; Ticket 07; `Docs/STATUS.md`; issue #61's earlier area-certificate comment; search/font-size tests and public Level 3 visual evidence.

## Verification

Demonstrate that larger sizes remain preferred when they fit; any smaller-size success is passed through the pinned renderer and actual glyph-bound check; inspect the final 728×90 PNG at native pixel scale; document legibility judgment separately from hard validation and PNG/hash reproducibility.

## Supersedes

Supersedes the numeric 10–12px “floor” in ADR-006 §3b and the matching imperative in `PROJECT_CONTRACT.md` §8 only. ADR-006's typed failure statuses and incomplete-versus-infeasible distinction are unchanged.

## Open external facts

No numeric readability threshold appears in the supplied PDF. The official score threshold, hidden target catalogue, and organizer's scoring weights remain unverified.
