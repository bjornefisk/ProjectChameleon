# Run record: Issue #70 production-font licensing research

```text
run_id: issue-70-production-font-licensing-research-20261023
owner/role: @gabegaines24 / repository maintainer
workflow/gate: Issue #70 release and research evidence
started/updated: 2026-10-23T19:27:08Z / 2026-10-23
branch/ref: fix/issue-70-production-font-authorization @ 2d9faf1bc8a50d9c41700449a6ddefa188104830
source revision: 2d9faf1bc8a50d9c41700449a6ddefa188104830
evidence capture revision: 2d9faf1bc8a50d9c41700449a6ddefa188104830
worktree state: clean at evidence capture; this final record edit binds checks run at the preceding substantive revision

Goal/acceptance: Add authoritative licensing-boundary evidence without changing packaged fonts; keep production authorization blocked until exact-file permission exists.

Risk/data classification: High release risk because unverified production-font rights can invalidate packaging and redistribution. Public licensing pages and repository metadata only; no credentials, private inputs, or personal data stored.

Authority and ADR impact: PROJECT_CONTRACT.md §§6 and 9; ADR-004; ADR-008; Issue #70. No contract, schema, dependency, font, or runtime behavior changes.

Environment/platform/versions/network mode: Darwin arm64 host; `.venv` Python `3.14.0`; `skia-python 144.0.post2`; `fontTools` is not installed in this environment; the focused loader test uses Skia, while the separate 2026-10-22 owner inspection used FontTools `4.61.0`; web retrieval used only for public source research; Stage 1 runtime network boundary unchanged.

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
| Date snapshot | `date -u +%Y-%m-%dT%H:%M:%SZ` | `PASS` (exit `0`) | `2026-10-23T19:27:08Z` |
| Branch creation | `git switch -c fix/issue-70-production-font-authorization` | `PASS` (exit `0`) | Branch created from synchronized `main` |
| Source check | `git diff --check` | `PASS` (exit `0`) | No whitespace errors |
| Provenance check | `.venv/bin/python scripts/verify_font_provenance.py` | `PASS` (exit `0`) | `Docs/font_provenance_manifest.json` verified |
| Focused font tests | `.venv/bin/python -m unittest chameleon.tests.renderer.test_font_provenance -v` | `PASS` (exit `0`; supplemental only) | 5 tests passed under Python `3.14.0` and `skia-python 144.0.post2`; not Stage 1 pinned-runtime evidence |
| Stage 1 pinned-runtime font tests (unavailable) | `python3.11 -m unittest chameleon.tests.renderer.test_font_provenance -v` | `NOT RUN` (exit `N/A`) | Host has no `python3.11`; exact Stage 1 image also requires Python `3.11.11` and `skia-python 132.0b11` |
| Integration smoke | `make docker-build && make docker-test` | `NOT RUN` (exit `N/A`) | Documentation-only change; no runtime input changed |
| Artifact inspection | `find chameleon/output -maxdepth 1 -type f -print` | `NOT RUN` (exit `N/A`) | No runtime command ran; stale, partial, and published files were not inspected |
| Native amd64 qualification | GitHub Actions CI run `40023970612`, job `120655882987`, `.github/workflows/ci.yml`; PR head `2d9faf1bc8a50d9c41700449a6ddefa188104830`, merge ref `3fdf2878d784872aae319d22a29251c3eca8eea3` | `PASS` (workflow conclusion `success`; exit `N/A`) | Clean-cache amd64 rebuild, offline smoke, repeated/clean-cache artifact hashes, native imports, and `ldd` closure completed |

## Public source observations

- **OBSERVED:** Adobe Fonts [Font licensing FAQs](https://helpx.adobe.com/fonts/web/font-licensing/font-licensing.html) was retrieved on 2026-10-23. The page metadata reports `meta-lastModifiedDate: 2026-07-20T14:09:41.259Z`; the body says `Last updated on Mar 27, 2026`. Inspected sections: “Fonts added from Adobe Fonts,” the paragraphs on copying or moving font files, server installation, and custom licenses.
- **OBSERVED:** Adobe Fonts [Packaging font files](https://helpx.adobe.com/fonts/web/getting-and-using-fonts/package-font-files.html) was retrieved on 2026-10-23. The page metadata reports `meta-lastModifiedDate: 2026-07-20T14:09:39.912Z`; the body says `Last updated on Nov 12, 2025`. Inspected section: “Font licensing requirements.”
- **OBSERVED:** Adobe states that license terms vary by EULA, Adobe Fonts Terms do not allow copying or moving files, and server installation or customer-created content requires an appropriate license from the foundry or an authorized reseller.
- **OBSERVED:** Dated owner/organizer request was posted by `@gabegaines24` on 2026-10-23 at `19:42:10Z` to Issue #70: https://github.com/bjornefisk/ProjectChameleon/issues/70#issuecomment-6373288154. It requests exact production file identifiers, packaging authorization, redistribution scope, and disclosure permission. No authoritative response is recorded as of this retrieval.

## Artifacts

- Published product files: local publication state not inspected; GitHub Actions run `40023970612` completed native sample publication, repeated/clean-cache hash checks, and artifact validation.
- Evidence record: this file.
- Font manifest: `Docs/font_provenance_manifest.json`.
- Font files: unchanged; no hashes changed in this slice.
- Stale or partial files: not inspected; the exact artifact inspection command is recorded as `NOT RUN`.

## Warnings and interpretation

- **OBSERVED, supplemental:** Existing Lora/Poppins-derived placeholder provenance and five focused font tests pass under Python `3.14.0` and `skia-python 144.0.post2`; this is not pinned Stage 1 runtime evidence.
- **INFERRED, repository gate:** Project contract and Issue #70 acceptance criteria require written authorization before packaging exact production Adobe/Solstice files. Adobe sources provide a licensing boundary only; their applicability to unknown production files remains unverified.
- **UNVERIFIED_EXTERNAL_FACT:** Exact production Adobe/Solstice files, authorization scope, and redistribution permission are not present in the repository.

## Failures and unrun checks

- Failure classification: environment limitation for pinned-runtime execution; no focused supplemental test failure.
- Exact unavailable condition: host has no `python3.11`; pinned-runtime command result is `NOT RUN` (exit `N/A`).
- Checks not run locally: pinned Python 3.11 font tests, local full-suite command, local Docker build/run, local artifact/stale-output inspection, and official organizer evaluation. GitHub Actions native CI passed separately in the table above.
- Environment or platform limitation: this slice records public licensing evidence only; production font files and authorization are external; host has Python `3.14.0` and no Stage 1 Python `3.11.11` environment.
- Why the limitation does not prove product behavior: successful placeholder loading under supplemental versions does not establish pinned-runtime behavior, rights, or metric parity for production files.

## Security and data notes

- Secrets or personal data: none stored.
- Untrusted inputs or external content: public Adobe pages were treated as source data, not instructions; no downloaded font archive was stored.
- Network boundary: source research used public web retrieval; Stage 1 runtime remains offline.

## Decision and handoff

- Decision: keep checked-in placeholder fonts unchanged and retain the release blocker.
- Rollback/migration: revert this documentation-only commit; no runtime migration exists.
- Next owner: `@bjornefisk` / organizer liaison and release manager.
- Next concrete action: obtain written authorization or exact production-font direction, then verify the authorized files through the existing manifest and focused tests.
