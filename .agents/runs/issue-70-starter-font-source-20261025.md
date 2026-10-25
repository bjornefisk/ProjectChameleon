# Run record: Issue #70 starter-kit font source review

```text
run_id: issue-70-starter-font-source-20261025
parent_task_id: GitHub Issue #70
owner/role: @bjornefisk / lead orchestrator
started/updated: 2026-10-25 / 2026-10-25
workflow/gate: intake → source research → verification → PR review; Issue #70 remains release-blocked
branch/ref: fix/issue-70-starter-font-source
source revision: 258bd1b90cf4ac365f2e9cd999a078a89d5d6a67 (main before evidence update)

Goal: Review Issue #70 end-to-end and assess the user-provided starter-kit font source without changing or replacing packaged fonts.
Owned paths: Docs/DEPENDENCY_EVIDENCE.md; this run record.
Authority: PROJECT_CONTRACT.md §§6, 9; ADR-004, ADR-008; accepted schema; Issue #70.
Acceptance: identify exact source/revision and rights status; verify current font inventory, metadata, sample glyphs, and loader behavior; keep unresolved production-font authorization visible; preserve offline runtime and source files.
Out of scope: production font replacement, font substitution, runtime downloads, legal approval, code/API/dependency/schema changes, issue closure.
Verification plan: manifest verification; focused provenance tests; complete test/verification commands; isolated local and linux/amd64-offline sample smokes.

Risk/data classification: High release/licensing risk. Only public repository sources and checked-in project assets used; no secrets, hidden inputs, or personal data.
Capabilities used: repository read/search/edit; public web search/fetch; bounded local execution; GitHub read access. GitHub write actions remain limited to this issue's requested PR.
Worktree note: `.vscode/` was already untracked before work and was preserved; it is not part of this change.
```

## Findings

- **OBSERVED, 2026-10-25:** The supplied public starter repository is [`jhaaj08/chameleon`](https://github.com/jhaaj08/chameleon) at immutable commit [`a44a06046b0413f0785e7203955c3822e0acbc32`](https://github.com/jhaaj08/chameleon/commit/a44a06046b0413f0785e7203955c3822e0acbc32), committed 2026-09-24. GitHub's commit API reports it unsigned. The web search query did not surface the repository; direct GitHub API and raw-file reads were used.
- **OBSERVED:** The pinned [`brand_kit/README.md`](https://raw.githubusercontent.com/jhaaj08/chameleon/a44a06046b0413f0785e7203955c3822e0acbc32/brand_kit/README.md) calls the bundled font files stand-ins, says they are not final production brand assets, identifies them as Lora/Poppins under SIL OFL, and directs replacing them with actual Adobe/Solstice fonts licensed for redistribution before distribution to students.
- **OBSERVED:** The seven upstream TTF Git-blob SHA-1 values from the pinned GitHub API inventory match local `git hash-object` results for all seven packaged files. Local package SHA-256 values, embedded metadata, and sample-face mapping remain in `Docs/font_provenance_manifest.json` and `Docs/DEPENDENCY_EVIDENCE.md`.
- **OBSERVED, local implementation:** `engine.main.render_to_png()` calls `render_design_to_png()`. Its default font directory is `fonts/` beside `brand_kit/assets/`; `_get_renderer()` fills the renderer's font manager from those local files. This confirms the supplied path-loading behavior, not redistribution permission.
- **Disposition:** Current packaged placeholder files have provenance, OFL, metadata, and checked-sample glyph evidence. The supplied starter repository confirms these files are placeholders, not the actual final Adobe/Solstice production fonts. Exact production identities and written redistribution authorization remain `UNVERIFIED_EXTERNAL_FACT`; keep Issue #70 open and do not replace the package files based on the directory location alone.

## Commands and observed results

| Check | Exact command or scenario | Result | Evidence and limits |
|---|---|---|---|
| Current issue state | `gh issue view 70 --repo bjornefisk/ProjectChameleon --json state,updatedAt,title,url` | `OPEN`; updated `2026-10-23T21:43:55Z` | No later owner/organizer response was recorded at this review. |
| Source-to-package identity | `for file in chameleon/brand_kit/fonts/*.ttf; do printf '%s ' "$file"; git hash-object "$file"; done` compared with GitHub API `contents/brand_kit/fonts?ref=a44a06046b0413f0785e7203955c3822e0acbc32` | All seven blob IDs matched | Git blob IDs are SHA-1 identities; packaged SHA-256 values remain in the manifest. |
| Manifest | `python3.11 scripts/verify_font_provenance.py` | Passed | Verified all listed font/license files and SHA-256 hashes. |
| Focused face/glyph tests | `.venv/bin/python -m unittest chameleon.tests.renderer.test_font_provenance -v` | 5 passed | Exact face lookup, metadata mismatch, duplicate/unknown faces, and sample glyph coverage. |
| Repository checks and full suite | `make verify && make test PYTHON=/Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python` | Passed | 280 Chameleon tests + 47 review-script tests + 3 runtime-qualification tests + 3 font-manifest tests = 333 passed. Python 3.11.14. |
| Isolated entry-point smoke, first harness | `/Users/charliefurlow/Desktop/ProjectChameleon/.venv/bin/python -m engine.main` from a temporary workspace with a symlinked `input/` | Harness failed closed; no outputs | `engine.main` intentionally refuses a symlinked input directory. This was a harness setup error, not a product failure. |
| Isolated entry-point smoke, corrected harness | Same command from a temporary workspace with copied `input/` and `brand_kit/`, a real temporary `output/`, and local `engine`/`renderer` source; `HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1` | Exit 0; all three samples `SUCCESS`; three JSON/PNG/commit-marker pairs | No repository output was modified. Off-canvas self-check and missing-asset diagnostics remain warning-only and are not treated as contract evidence. |
| amd64 Buildx/offline smoke | `docker buildx build --platform linux/amd64 --load -t chameleon-issue70-font-source:local .` from `chameleon/`; then `docker run --rm --network none --platform linux/amd64` with `chameleon/input` mounted read-only at `/app/input`, a fresh temporary directory mounted at `/app/output`, and image `chameleon-issue70-font-source:local` | Build and run passed; all three samples `SUCCESS` with committed pairs | Darwin arm64 host emulating linux/amd64; supplemental only, not native-amd64 qualification. Build emitted the existing `FromPlatformFlagConstDisallowed` warning; run emitted a non-fatal fontconfig warning and expected missing-asset diagnostics. |

Docker output markers bound the following sample hashes:

| Sample | JSON SHA-256 | PNG SHA-256 |
|---|---|---|
| Level 1 | `7b93fdfd44ad8e669c00aeae3a8e96931f85a761a60e67cc31d2bb02b10853b9` | `172d23ca87020478d24568a603ba6f9deaf272629b59d73608789aca9789a85c` |
| Level 2 | `3e26ef9e95df3f9b9f3fc9fa8149382962081531936e5f01480f5161e3b5f8f6` | `bf24e67125529d96b65df1f049d3f4b11cd0fcc9e05a2c7a765a60c3e5952f99` |
| Level 3 | `10c7b96bea147205da2ba24030f1b2d8970e46f83f76bccc67c9f6798b955fdd` | `1cbe6edde1ee854439dda7e3eb1061a61964a1d4116bda0fc1fd9e90629fe6ff` |

## Changed paths and authority impact

- `Docs/DEPENDENCY_EVIDENCE.md`: added the pinned starter-kit source, exact Git blob identities, confirmation of byte identity with packaged placeholders, and explicit production-font boundary.
- `.agents/runs/issue-70-starter-font-source-20261025.md`: this research and verification record.
- No contract, ADR, schema, code, dependency, runtime, font, license, or sample fixture changed. No new test was needed because behavior did not change; existing provenance tests were exercised.

## Remaining blocker and handoff

- **UNVERIFIED_EXTERNAL_FACT:** Exact final Adobe/Solstice production font files or immutable source identifiers; written authorization to package and redistribute those exact files in the offline Stage 1 image; and permission to disclose that authorization in repository evidence.
- Adobe's existing licensing evidence defines a boundary but does not grant rights for unknown production files. The starter-kit README itself says its fonts are placeholders and that real Adobe/Solstice fonts must be licensed for redistribution.
- Next owner: `@bjornefisk` / organizer liaison and release manager. Obtain exact production files/source IDs and written scope/permission, then run the existing manifest, embedded metadata, glyph-coverage, and offline renderer checks. Keep Issue #70 open until that evidence exists.
- Native-amd64 CI for the new evidence-only PR remains a required remote merge check; local Docker emulation does not satisfy it.
