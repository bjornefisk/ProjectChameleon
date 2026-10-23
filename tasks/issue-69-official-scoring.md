# Issue #69 work plan: official scoring evidence

## Scope

Replace unsupported local qualification claims with organizer-authoritative
scoring evidence across Levels 1, 2, and 3, or preserve the blocker with a
dated request and explicit impact.

This draft PR establishes the issue-specific work branch. It does not claim an
official score and does not include hidden evaluation inputs.

## Ordered slices

1. Request the official evaluator protocol, thresholds, target catalogue,
   hardware constraints, failure semantics, and result format.
2. Confirm whether the protocol and results may be disclosed publicly.
3. Record the request source, date, response, permission, and blocker impact.
4. Freeze a release candidate only after font authorization and dependency
   qualification are complete.
5. If authorized, run the frozen candidate through the official process.
6. Record per-level score, threshold, hard-valid rate, failure status, runtime,
   evaluator revision, tested commit, and disclosure permission.
7. If access is denied or unavailable, retain `UNVERIFIED_EXTERNAL_FACT` and
   leave this issue blocked.

## Acceptance criteria

- Official source, evaluator revision, and scoring rubric are recorded.
- Results bind to one immutable candidate commit.
- Levels 1, 2, and 3 are reported separately.
- Official scoring remains separate from local authored and held-out-style
  corpora.
- No hidden input or confidential result is stored in the public repository.
- No issue closure occurs without authoritative evidence or a documented
  organizer denial.

## Verification

- Review source authority and disclosure permission.
- Confirm frozen commit and evaluator revision in every reported result.
- Review `Docs/STATUS.md`, `Docs/DEPENDENCY_EVIDENCE.md`, and `.agents/runs/`.
- Keep local smoke and hard-validation evidence separate from official scoring.

## Dependencies and non-goals

- Candidate freeze depends on Issues #70 and #71 evidence gates.
- Do not invent thresholds, organizer limits, or hidden-task behavior.
- Do not tune implementation to public samples as a proxy for official scoring.
- Do not add model, solver, or evaluator runtime scope.

## PR lifecycle

Use `Refs #69` while this PR is in progress. Convert to ready only after
implementation and evidence exist. Close Issue #69 after acceptance evidence,
then squash-merge into `main`; delete this branch after merge.
