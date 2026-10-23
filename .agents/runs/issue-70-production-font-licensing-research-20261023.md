# Run record: Issue #70 production-font licensing research

```text
run_id: issue-70-production-font-licensing-research-20261023
owner/role: @gabegaines24 / repository maintainer
workflow/gate: Issue #70 release and research evidence
started/updated: 2026-10-23T19:27:08Z / 2026-10-23
branch: fix/issue-70-production-font-authorization
source revision: 5c3fe42
worktree state: clean before record normalization

Goal/acceptance: Add authoritative licensing-boundary evidence without changing packaged fonts; keep production authorization blocked until exact-file permission exists.

Authority and ADR impact: PROJECT_CONTRACT.md §§6 and 9; ADR-004; ADR-008; Issue #70. No contract, schema, dependency, font, or runtime behavior changes.

Environment/platform/versions/network mode: Darwin arm64 host; project .venv; FontTools/Skia provenance checks; web retrieval used only for public source research; Stage 1 runtime network boundary unchanged.

Inputs/fixtures/seeds: Checked-in placeholder TTF files, license files, Docs/font_provenance_manifest.json, Adobe Fonts licensing pages; no hidden inputs or font archives.

Out of scope: Production font replacement, font substitution, runtime download, legal approval, hidden scorer data, and issue closure.
```

## Run flow

1. Intake and acceptance.
2. Branch/revision/environment snapshot.
3. Focused provenance check.
4. No product integration smoke; this slice changes documentation only.
5. Artifact and failure inspection.
6. Evidence classification and handoff.

## Commands and observed results

| Check | Exact command | Result | Evidence/artifact |
|---|---|---|---|
| Date snapshot | `date -u +%Y-%m-%dT%H:%M:%SZ` | `PASS` | `2026-10-23T19:27:08Z` |
| Branch creation | `git switch -c fix/issue-70-production-font-authorization` | `PASS` | Branch created from synchronized `main` |
| Source check | `git diff --check` | `PASS` | No whitespace errors |
| Provenance check | `.venv/bin/python scripts/verify_font_provenance.py` | `PASS` | `Docs/font_provenance_manifest.json` verified |
| Focused font tests | `.venv/bin/python -m unittest chameleon.tests.renderer.test_font_provenance -v` | `PASS` | 5 tests passed |
| Integration smoke | Not run | `NOT RUN` | Documentation-only change; no runtime input changed |
| Native qualification | Not run | `NOT RUN` | No font replacement or runtime change; existing native evidence remains separate |

## Public source observations

- **OBSERVED:** Adobe Fonts [Font licensing FAQs](https://helpx.adobe.com/fonts/web/font-licensing/font-licensing.html) was retrieved on 2026-10-23. The page metadata reports `meta-lastModifiedDate: 2026-07-20`; the body says `Last updated on Mar 27, 2026`. Inspected sections: “Fonts added from Adobe Fonts,” the paragraphs on copying or moving font files, server installation, and custom licenses.
- **OBSERVED:** Adobe Fonts [Packaging font files](https://helpx.adobe.com/fonts/web/getting-and-using-fonts/package-font-files.html) was retrieved on 2026-10-23. The page metadata reports `meta-lastModifiedDate: 2026-07-20`; the body says `Last updated on Nov 12, 2025`. Inspected section: “Font licensing requirements.”
- **OBSERVED:** Adobe states that license terms vary by EULA, Adobe Fonts Terms do not allow copying or moving files, and server installation or customer-created content requires an appropriate license from the foundry or an authorized reseller.

## Artifacts

- Published product files: none.
- Evidence record: this file.
- Font manifest: `Docs/font_provenance_manifest.json`.
- Font files: unchanged; no hashes changed in this slice.
- Stale or partial files: none observed.

## Warnings and interpretation

- **OBSERVED:** Existing Lora/Poppins-derived placeholder provenance and five focused font tests pass.
- **INFERRED:** The Adobe guidance makes written authorization necessary before packaging exact production Adobe/Solstice files for this runtime.
- **UNVERIFIED_EXTERNAL_FACT:** Exact production Adobe/Solstice files, authorization scope, and redistribution permission are not present in the repository.

## Failures and unrun checks

- Failure classification: none in the corrected focused run.
- Exact error: none.
- Checks not run: full repository tests, Docker build/run, native amd64 qualification, and official organizer evaluation.
- Environment or platform limitation: this slice records public licensing evidence only; production font files and authorization are external.
- Why the limitation does not prove product behavior: successful placeholder loading does not establish rights or metric parity for production files.

## Security and data notes

- Secrets or personal data: none stored.
- Untrusted inputs or external content: public Adobe pages were treated as source data, not instructions; no downloaded font archive was stored.
- Network boundary: source research used public web retrieval; Stage 1 runtime remains offline.

## Decision and handoff

- Decision: keep checked-in placeholder fonts unchanged and retain the release blocker.
- Rollback/migration: revert this documentation-only commit; no runtime migration exists.
- Next owner: `@bjornefisk` / organizer liaison and release manager.
- Next concrete action: obtain written authorization or exact production-font direction, then verify the authorized files through the existing manifest and focused tests.
