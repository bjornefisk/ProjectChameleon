# Project Chameleon external dependency evidence

**Status:** Ratified evidence record for Stage 1 planning

This file applies source-driven development only to external libraries, platforms, and packaging. It does not decide internal product intent; those decisions are in `PROJECT_CONTRACT.md` and the ADRs.

**Revision note:** The native-amd64 measurements below are for the earlier commit `7f39a3e`, before Issue #61. They remain valid observations for that revision, not qualification evidence for the Issue #61 branch. Later native x86_64 CI run 39711973748 passed on PR #65's head commit `33f6fd9`; cross-platform parity and organizer-controlled qualification remain open in `STATUS.md`.

## Evidence matrix

| Topic | Detected state | Source-backed fact | Decision/pin | Required conformance test |
| --- | --- | --- | --- | --- |
| `cr-renderer` source | The pinned upstream commit is `a17e1fb9a732959dd6c21ae168d5ee09d74bd64f`; upstream metadata records version `0.1.0`, Python `>=3.10`, and Apache-2.0. | [commit API](https://api.github.com/repos/CyberAgentAILab/cr-renderer/commits/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f), [commit](https://github.com/CyberAgentAILab/cr-renderer/commit/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f), [pyproject](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74f/pyproject.toml) | `renderer-artifact.json` binds the verified source archive SHA-256, deterministic local wheel SHA-256, and PEP 610 installed provenance. Treat future upgrades as a renderer ADR. | Build and import the local wheel on amd64; require its installed archive hash to match the manifest and render the golden fixtures. |
| Upstream renderer geometry | `CrelloV5Renderer` translates absolute `left/top`, rotates around the local center in degrees, draws images into the destination rectangle, and downsizes to `max_size`. | [renderer.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74f/src/cr_renderer/renderer.py) | Contract against the pinned source plus the local adapter. Do not assume intrinsic contain/cover or automatic wrapping in upstream. | Non-square image, 90°/non-right-angle rotation, alpha, canvas scaling, and deterministic PNG tests. |
| Upstream text | `lineMap` supplies line ranges; absent map becomes one line. Line origins use `line_index * fontSize * lineHeight`; glyph advances include letter spacing; alignment is applied inside width. `wordBreak` is not used by the render path. | [schema.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/schema.py), [text_utils.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74f/src/cr_renderer/text_utils.py) | Keep public Chameleon text unchanged; the adapter owns deterministic line-map generation. | Explicit two-line map, missing map, all alignments, spacing, style maps, and glyph-bound tests. |
| Local text adapter | The wrapper measures effective style spans, preserves code-point `[start,end)` runs, intersects UAX #29 clusters with UAX #14 opportunities, enforces explicit line/height limits, and rejects malformed or unbreakable text. | `chameleon/renderer/converter/wrap.py`, `convert.py`, `unicode_data.py` | Keep adapter behavior aligned with ADR-008 and the pinned renderer. | Boundary/style/spacing/height, Unicode property, non-breaking class, malformed-input, and glyph-bound tests. |
| Unicode text properties | The adapter's grapheme, Indic conjunct, line-break, general-category, and East Asian width decisions use generated Unicode 17.0.0 tables from the official UCD files. | [GraphemeBreakProperty.txt](https://www.unicode.org/Public/17.0.0/ucd/auxiliary/GraphemeBreakProperty.txt), [emoji-data.txt](https://www.unicode.org/Public/17.0.0/ucd/emoji/emoji-data.txt), [DerivedCoreProperties.txt](https://www.unicode.org/Public/17.0.0/ucd/DerivedCoreProperties.txt), [LineBreak.txt](https://www.unicode.org/Public/17.0.0/ucd/LineBreak.txt), [UnicodeData.txt](https://www.unicode.org/Public/17.0.0/ucd/UnicodeData.txt), [EastAsianWidth.txt](https://www.unicode.org/Public/17.0.0/ucd/EastAsianWidth.txt) | Keep tables versioned with the adapter; upgrade only with renderer conformance evidence. | UAX #29 cluster cases, UAX #14 GL/WJ/BA/punctuation cases, and repeated deterministic wrapping. |
| Renderer transitives | The selected upstream `uv.lock` records `datasets 3.2.0`, `pydantic 2.10.6`, `skia-python 132.0b11`, `Pillow 11.1.0`, and `numpy 2.2.2`; project metadata alone gives lower bounds. | [upstream pyproject](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/pyproject.toml), [upstream lock](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74f/uv.lock) | Keep direct constraints in `requirements.in`; `requirements.lock` hash-locks the complete runtime closure. `renderer-build.lock` hash-locks the PEP 517 build environment. | Prepare the target wheelhouse, record `pip freeze`/`pip inspect`, verify imports, local font loads, sample render, and clean-cache native amd64 evidence. |
| Pillow | The prior requirement was `Pillow>=10.0`. Official support lists Python 3.11 for Pillow 10, 11, and 12. | [Pillow Python support](https://pillow.readthedocs.io/en/stable/installation/python-support.html) | Pin `Pillow==11.1.0` for parity with the selected renderer lock. | Decode all packaged assets; exercise RGBA conversion, LANCZOS contain/cover/fill, shape rasterization, placeholder, and PNG round-trip. |
| Skia Python binding | Skia was transitive and lower-bounded at `>=120.0b5`; the selected lock recorded `132.0b11`. | [skia-python 132.0b11](https://pypi.org/project/skia-python/132.0b11/), [Skia download/build](https://skia.org/docs/user/download/) | Pin `skia-python==132.0b11`; verify native libraries in the target image. | Import Skia, create a CPU surface, load each TTF, render text/image/rotation, encode PNG. |
| PNG golden runtime | The official image uses Python 3.11.11; persisted renderer and engine hashes bind Python 3.11, renderer revision, Pillow, Skia, and fonts. | [`chameleon/Dockerfile`](../chameleon/Dockerfile), [CI workflow](../.github/workflows/ci.yml), [`requirements.lock`](../chameleon/requirements.lock), [golden fixtures](../chameleon/tests/fixtures/) | Local setup defaults to `python3.11`; `make test` rejects another minor. PNG hashes remain per-OS/machine evidence, not universal parity. | Run renderer and engine hash cases in each recorded environment; preserve contract/artifact checks and fail on environment or hash drift. |
| Datasets/Pydantic | Both were transitive and lower-bounded by `cr-renderer`; the selected lock recorded `datasets==3.2.0` and `pydantic==2.10.6`. | [cr-renderer pyproject](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/pyproject.toml) and lock above | Pin the selected versions because the adapter uses `datasets` feature types and upstream Pydantic models. | Import `CrelloV5Renderer`, exercise the feature stub, and render with an empty and non-empty element list. |
| JSON Schema validator | No validator dependency existed in the starter. | [jsonschema Draft 2020-12 docs](https://python-jsonschema.readthedocs.io/en/stable/validate/) | Pin `jsonschema==4.23.0` for contract tests using `Draft202012Validator`. | Validate the schema itself, all sample sources, empty design, and negative structural cases. |
| Python JSON numeric ingress | `json.load` passes the original numeric token text to `parse_int` and `parse_float`; the default float path creates binary floats, and `parse_constant` handles non-standard `NaN`/`Infinity` tokens. | [Python 3.11 `json` documentation](https://docs.python.org/3.11/library/json.html#json.load) | Use `parse_int=int`, `parse_float=Decimal`, and a rejecting `parse_constant` hook before validation and geometry. | Runner-seam cases for finite decimal, exponent, integer, and non-finite-constant inputs; serialize mutable geometry/font-size values as finite integers while retaining only contract-approved immutable values. |
| OR-Tools CP-SAT | Absent from requirements, imports, and code; present only in proposed architecture. | [CP-SAT guide](https://developers.google.com/optimization/cp/cp_solver), [Python API](https://or-tools.github.io/docs/pdoc/ortools/sat/python/cp_model.html), [release metadata](https://pypi.org/pypi/ortools/9.15.6755/json) | Do not add it during ratification. If selected later, pin a release and test integer intervals, status paths, allowed overlaps, and rotated post-validation. | Tiny deterministic model plus solver-status and geometry-validator checks. |
| Docker platform | The starter forced `linux/amd64` but used a mutable base tag. Docker documents `--platform` selection and QEMU emulation for non-native builds; a `docker-container` Buildx builder does not automatically load its result into the local image store. | [Docker multi-platform builds](https://docs.docker.com/build/building/multi-platform/), [base-image pinning](https://docs.docker.com/build/building/best-practices/#pin-base-image-versions), [Buildx `--load`](https://docs.docker.com/reference/cli/docker/buildx/build/#load) | Keep a single amd64 scoring artifact. Pin `python:3.11.11-slim-bookworm` to the observed OCI index digest in `Dockerfile`; use `--load` for the local build-then-run smoke path; qualify the amd64 child digest during build. | Buildx amd64 build on Apple Silicon and native amd64; inspect `uname -m`, Python patch, wheel architecture, and sample PNG. |
| Python base image | `python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5`; amd64 child `sha256:a8e0a3090316aed0b11037aac613aef32fb1747dcc1dcb5c0f6c727a0113a07f`. | [Docker Hub image metadata](https://hub.docker.com/v2/repositories/library/python/tags/3.11.11-slim-bookworm) | Pin the manifest digest and explicit `linux/amd64` target; `renderer-artifact.json` also records the child digest and Python `3.11.11`. | Record image digest/SBOM, Python version, native imports, and clean rebuild result. |
| Debian package closure | The image replaces inherited sources with timestamped Bookworm and Bookworm Security snapshots, installs four exact roots, and adds 54 exact packages without upgrades. | `chameleon/apt/sources.list`, `packages.lock`, `packages.sha256`, and `snapshot-evidence.json` record source URLs, signed InRelease hashes, exact versions, archive hashes, keyring, and Valid-Until handling. | Verify apt signatures, exact archive hashes, complete `dpkg-query` closure, and copyright notices for the installed packages. | Rebuild on native amd64; compare locked package closure, archive hashes, notices, SBOM, and `ldd` output. |
| SBOM generation | The GitHub runner does not provide `docker sbom`; CI uses the pinned `anchore/sbom-action` commit `e22c389904149dbc22b58101806040fa8d37a610`, which embeds Syft `v1.42.3`, to scan the locally loaded image and emit SPDX JSON. | [sbom-action README](https://github.com/anchore/sbom-action/blob/e22c389904149dbc22b58101806040fa8d37a610/README.md), [action metadata](https://raw.githubusercontent.com/anchore/sbom-action/e22c389904149dbc22b58101806040fa8d37a610/action.yml), [pinned commit](https://github.com/anchore/sbom-action/commit/e22c389904149dbc22b58101806040fa8d37a610) | Pin the action commit and Syft version; keep artifact upload and dependency submission disabled for qualification. | Native amd64 workflow emits and hashes a non-empty SPDX JSON image SBOM without runtime network access. |
| Runtime qualification harness | `scripts/qualify_runtime.py` records child wall time, CPU time, maximum RSS with units, Linux peak observed child-thread count from `/proc/<pid>/status`, return code, and platform metadata; it atomically writes the JSON report. CI runs it inside the pinned image with `--network none`, records image size and packaged asset/font hashes, checks native-library `ldd` closure, validates the report and artifact set, and compares repeated and clean-cache sample artifact hashes. | Repository script and `.github/workflows/ci.yml` | Record observations without converting organizer-controlled resource limits into hard runtime gates. | Native amd64 CI run; report schema and expected statuses; repeat hashes; clean-cache image run; image-size, CPU, RSS, thread, latency, asset/font, and native-library logs. |
| Font loading | The project scans local TTF/OTF files and injects bytes into private `FontManager._fonts`; upstream default construction can download font data. | [upstream fonts.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/fonts.py) | Keep fonts in the image and use explicit local loading. Treat private-manager integration as revision-sensitive. | Hash every declared font, verify family/weight/style lookup, unknown-face failure behavior, and glyph advances. |
| Offline Hugging Face behavior | `datasets[vision]` is transitive; no model or weights are present. | [Hugging Face offline variables](https://huggingface.co/docs/huggingface_hub/main/package_reference/environment_variables#hfhuboffline) | Stage 1 has no model dependency. Future model work must use immutable local artifacts and offline controls. | Empty caches + `HF_HUB_OFFLINE=1` + `--network none`; audit for attempted downloads. |
| Adobe Express add-on | No manifest, JS package graph, or add-on source exists. | [Add-on architecture](https://developer.adobe.com/express/add-ons/docs/guides/learn/platform-concepts/architecture), [UI SDK](https://developer.adobe.com/express/add-ons/docs/references/addonsdk/), [Document APIs](https://developer.adobe.com/express/add-ons/docs/references/document-sandbox/document-apis/), [Manifest v2](https://developer.adobe.com/express/add-ons/docs/references/manifest/) | Finale-only. When implemented, use the documented iframe/UI and document-sandbox split, manifest v2/API 1, and a separate npm lock. | Manifest, SDK readiness, sandbox/UI proxy, permissions, serialization, and no experimental API in release. |
| Adobe fonts | Stage 1 uses packaged TTF bytes, not Express document fonts. | [Express font API](https://developer.adobe.com/express/add-ons/docs/references/document-sandbox/document-apis/classes/fonts), [text guide](https://developer.adobe.com/express/add-ons/docs/guides/learn/how-to/use-text) | Do not promise Stage 1/Express metric parity or silent font substitution. | Resolve exact PostScript faces in entitled/unentitled accounts before finale typography claims. |
| Challenge hardware/model limits | Rules name Apple M5 Pro and leave CPU/RAM/disk/GPU and model allowlist/size unresolved. No model runtime or weights are in the repository. | Repository facts: `chameleon/RULES.md`; external platform docs cannot establish organizer limits. | Keep these as open external blockers; do not invent limits. | Await organizer specification, then add resource and deterministic-runtime tests. |

## Issue #70 packaged-font provenance and redistribution (initial evidence: 2026-10-22; starter-kit source addendum: 2026-10-25)

**Task:** Issue #70. **Verification run:** `PR-73-font-provenance-fix`. The run uses
the local Darwin arm64 environment and pinned project font files. It is local
evidence, not native-amd64 or organizer qualification.

### Source and redistribution terms

- **OBSERVED, source retrieval 2026-10-22 — Lora 3.008:** Google Fonts
  [`METADATA.pb` at `b2f711240d262008a28fb639ff31211ba1ff540b`](https://github.com/google/fonts/blob/b2f711240d262008a28fb639ff31211ba1ff540b/ofl/lora/METADATA.pb)
  records source repository [`cyrealtype/Lora-Cyrillic` at
  `403b1a66ca2e79f81d749c5299559e168591a4df`](https://github.com/cyrealtype/Lora-Cyrillic/tree/403b1a66ca2e79f81d749c5299559e168591a4df),
  dated 2023-12-14, with `fonts/variable/Lora[wght].ttf` and
  `fonts/variable/Lora-Italic[wght].ttf`. The cited metadata revision is
  immutable and maps the local Lora source files.
- **OBSERVED, source retrieval 2026-10-22 — Poppins 4.004:** Google Fonts
  [`OFL.txt` at the 4.004 release](https://raw.githubusercontent.com/google/fonts/7dc16b7de42db624b902f2292b68ed9e489e5053/ofl/poppins/OFL.txt)
  supplies the bundled 2020 copyright notice. Google Fonts
  [`METADATA.pb` at `4d560ddf8585f187eb2e959ca9847e2da3d82c16`](https://github.com/google/fonts/blob/4d560ddf8585f187eb2e959ca9847e2da3d82c16/ofl/poppins/METADATA.pb),
  dated 2025-11-07, records source repository commit
  [`itfoundry/Poppins` `738d9d691b66f1ad917123c58df104d16c74e1a7`](https://github.com/itfoundry/Poppins/tree/738d9d691b66f1ad917123c58df104d16c74e1a7).
  The source-face revision and Google Fonts license-package revision are
  distinct and intentionally recorded separately.
- **OBSERVED, owner inspection 2026-10-22:** FontTools 4.61.0 instances at
  Lora weights 400 and 700, plus the Poppins static faces, matched local
  glyph outlines, metrics, Unicode mappings, OS/2 data, and layout tables.
  Local family/name records identify the requested Solstice faces.
- **OBSERVED, repository verification run `PR-73-font-provenance-fix`:**
  `python3 scripts/verify_font_provenance.py` checks every listed TTF/license
  path, rejects missing or extra files, and compares SHA-256 values.
- **INFERRED:** Both bundled license texts permit modification and redistribution
  with software under OFL 1.1 conditions. This is evidence for these exact
  placeholder files, not legal approval for future production fonts.

### Official production-font licensing boundary

- **OBSERVED, Adobe Fonts FAQ retrieved 2026-10-23:** [Font licensing FAQs](https://helpx.adobe.com/fonts/web/font-licensing/font-licensing.html), publisher Adobe, page metadata `meta-lastModifiedDate: 2026-07-20T14:09:41.259Z`, body date `Last updated on Mar 27, 2026`. Inspected “Fonts added from Adobe Fonts” and the paragraphs on copying or moving font files, server installation, and custom licenses. Adobe states that its rules apply to fonts added through an Adobe account, Adobe Fonts Terms do not permit copying or moving font files to another user or computer, and server installation or customer-created content requires an appropriate license from the foundry or an authorized reseller. Adobe exposes no immutable page revision or content hash in the retrieved page; retrieval timestamp and metadata are the available source binding.
- **OBSERVED, Adobe Fonts packaging guidance retrieved 2026-10-23:** [Packaging font files](https://helpx.adobe.com/fonts/web/getting-and-using-fonts/package-font-files.html), publisher Adobe, page metadata `meta-lastModifiedDate: 2026-07-20T14:09:39.912Z`, body date `Last updated on Nov 12, 2025`. Inspected “Font licensing requirements.” Adobe states that font EULAs vary, many do not permit sending font files to third parties, and Adobe Fonts Terms do not allow copying or moving the files. Adobe exposes no immutable page revision or content hash in the retrieved page; retrieval timestamp and metadata are the available source binding.
- **INFERRED, repository gate:** Project contract and Issue #70 acceptance criteria require written authorization before packaging exact production Adobe/Solstice files. Adobe sources provide a licensing boundary only; their applicability to unknown production files remains unverified. **UNVERIFIED_EXTERNAL_FACT:** The sources do not identify exact production files, grant this repository a license, or replace written owner/foundry authorization. The checked-in Lora/Poppins-derived placeholder files remain governed by their separate OFL evidence above.

The research record is [`.agents/runs/issue-70-production-font-licensing-research-20261023.md`](../.agents/runs/issue-70-production-font-licensing-research-20261023.md). No production font files changed. Final Adobe/Solstice file availability, authorization scope, and redistribution permission remain **UNVERIFIED_EXTERNAL_FACT**.

### Starter-kit source identity (retrieved 2026-10-25)

The user-provided starter repository is [`jhaaj08/chameleon` at commit
`a44a06046b0413f0785e7203955c3822e0acbc32`](https://github.com/jhaaj08/chameleon/commit/a44a06046b0413f0785e7203955c3822e0acbc32),
whose commit date is 2026-09-24. Its [`brand_kit/README.md` at that
revision](https://raw.githubusercontent.com/jhaaj08/chameleon/a44a06046b0413f0785e7203955c3822e0acbc32/brand_kit/README.md)
explicitly describes the bundled fonts as stand-ins, not final production
brand assets, identifies them as Lora and Poppins under SIL OFL, and instructs
replacing them with actual Adobe/Solstice fonts licensed for redistribution
before distributing the starter to students. This is provenance for the
placeholder files, not a production-font authorization. The GitHub API reports
the commit as unsigned; its immutable commit ID is used here as the source
revision, not as a publisher signature.

The pinned [`brand_kit/fonts` inventory](https://api.github.com/repos/jhaaj08/chameleon/contents/brand_kit/fonts?ref=a44a06046b0413f0785e7203955c3822e0acbc32)
contains these seven TTFs. Each GitHub Git-blob SHA-1 matches `git hash-object`
of the corresponding packaged file in this repository, proving byte identity.
The package SHA-256 values remain in
[`font_provenance_manifest.json`](font_provenance_manifest.json).

| Font file | Starter-kit Git-blob SHA-1 (matches packaged file) |
| --- | --- |
| `SolsticeSerif-Regular.ttf` | `998fd8ed2d0d3a1162634beaeb24df3eb900c4a5` |
| `SolsticeSerif-Bold.ttf` | `8c8a27ce26b0485ece782019880654b9151b9092` |
| `SolsticeSerif-Italic.ttf` | `4f67a9cf3f45652707734df6df3116cb43337559` |
| `SolsticeSans-Regular.ttf` | `aa517771d2ed9157a28ee710a4c6b4b72cbf1d16` |
| `SolsticeSans-Bold.ttf` | `2a3af3eb105d071c1779401e3d0bc4991dbc2767` |
| `SolsticeSans-Italic.ttf` | `a13172da6966fde624b4e2a2c31d14c93ea5c2f4` |
| `SolsticeSans-BoldItalic.ttf` | `196e6fbe8343509a490aec6a51bef15a768f0de4` |

**OBSERVED, local code:** `engine.main.render_to_png()` delegates to
`renderer.converter.convert.render_design_to_png()`. When no font directory is
passed, the converter resolves `fonts/` beside `brand_kit/assets/` and loads
the files locally through `load_brand_font_manager()`; this confirms the
reported runtime path. It proves loading behavior only, not font rights.

**Disposition:** The packaged placeholders have source, metadata, sample-glyph,
and OFL evidence above. The starter repository confirms they are not the final
Adobe/Solstice production fonts. Exact production file identities and written
authorization for packaging/redistribution remain
**UNVERIFIED_EXTERNAL_FACT**. Do not replace the placeholders or close Issue
#70 based on the starter-kit path alone.

### File inventory and embedded metadata

Weights are embedded OS/2 weight classes; names and versions come from the TTF
name table. “Sample” means a face declared by one of three checked-in samples.

| Packaged path | SHA-256 | Embedded family / subfamily; weight; version | Sample |
| --- | --- | --- | --- |
| `chameleon/brand_kit/fonts/SolsticeSerif-Regular.ttf` | `b7eb2a832ae91824a7c670469f4a4e0c4910a3ceedc1d31aad07ea2bc336d2a7` | Solstice Serif / Regular; 400; 3.008 | No |
| `chameleon/brand_kit/fonts/SolsticeSerif-Bold.ttf` | `837d42cc1b336364b69714c73288a0ec7ceded41c137d5f62943df5f0745551a` | Solstice Serif / Bold; 700; 3.008 | Yes |
| `chameleon/brand_kit/fonts/SolsticeSerif-Italic.ttf` | `07526ca6ef70e5a7853abcdd614aeb62cdb958ed0cabc0f771f85094b4c67ccf` | Solstice Serif / Italic; 400; 3.008 | No |
| `chameleon/brand_kit/fonts/SolsticeSans-Regular.ttf` | `4500567b25fc1af2983cee01c1e57e01a0108b8b3844c182936d14c7dec7f69c` | Solstice Sans / Regular; 400; 4.004 | Yes |
| `chameleon/brand_kit/fonts/SolsticeSans-Bold.ttf` | `609a215925701021b97578c71702bfc492882556ce05602b670aaa74a32a1156` | Solstice Sans / Bold; 700; 4.004 | Yes |
| `chameleon/brand_kit/fonts/SolsticeSans-Italic.ttf` | `848a0433face0f273e313e4fdb3497a764f3c96b3b6670dffcc3cc38dcc83f2a` | Solstice Sans / Italic; 400; 4.004 | No |
| `chameleon/brand_kit/fonts/SolsticeSans-BoldItalic.ttf` | `e47af214406befc181508cf7ff87b774a955a670f7a54d8563a9757d45b2167d` | Solstice Sans / Bold Italic; 700; 4.004 | No |

### Sample face and glyph verification

- **OBSERVED, owner inspection 2026-10-22:** The three samples require
  `SolsticeSerif-Bold.ttf` (35 distinct codepoints),
  `SolsticeSans-Regular.ttf` (35), and `SolsticeSans-Bold.ttf` (33).
  Skia 132.0b11 mapped every required codepoint to a nonzero glyph ID;
  the Serif Bold sample includes U+2014.
- **OBSERVED, focused repository test 2026-10-23:** `.venv/bin/python -m
  unittest chameleon.tests.renderer.test_font_provenance -v` passed five tests.
  The test derives the three sample face sets from checked-in JSON and verifies
  every glyph through the exact local face lookup. Other scripts, unseen inputs,
  and unused faces remain outside this result.

The exact local font files, metadata, source-face tables, license copies, and
sample codepoints were inspected on 2026-10-22. Final Adobe/Solstice production
font availability and authorization remain **UNVERIFIED_EXTERNAL_FACT**.
Release manager must obtain written production-font direction before release.

### Current repository-submission and production-font disposition (2026-10-30)

The current Stage 1 repository submission packages seven Lora 3.008/Poppins 4.004 stand-in faces under the sample's Solstice Serif/Sans names. These are placeholders, not final Adobe/Solstice production fonts. Production-font integration and authorization are deferred until the exact production files and applicable written redistribution terms are supplied. No production-font authorization or official qualification is claimed. Issue #70 remains open as a production-release gate, not a blocker to repository-link-only submission. The separate student-distribution instruction in `chameleon/brand_kit/README.md` is unchanged and not waived.

**OBSERVED, local recheck on `origin/main` base `36c3e11c785e588f92671b8035e27463d8713b2c` (2026-10-30):**

- `python3 scripts/verify_font_provenance.py` passed. It checks the exact TTF/license inventory and SHA-256 values for all seven font files and both bundled OFL files against `Docs/font_provenance_manifest.json`.
- `git hash-object` over the seven packaged TTFs reproduced all seven pinned starter-kit Git-blob SHA-1 values in the table above, for starter commit `a44a06046b0413f0785e7203955c3822e0acbc32`.
- `.venv/bin/python -m unittest chameleon.tests.renderer.test_font_provenance -v` passed all five tests under Python 3.11.14 and Skia 132.0b11. Loading the full font directory checks embedded family/weight/style against filename mappings; tests also reject metadata/mapping errors, verify the exact bold-italic face, and find nonzero glyph IDs for every codepoint in the three checked samples.
- Both bundled OFL files are present, their manifest SHA-256 values match, and their text identifies SIL Open Font License 1.1. **INFERRED, placeholders only:** redistribution is subject to those OFL conditions; this is not legal review or authorization for production fonts.
- FontTools is unavailable in this local environment, so the full name/version/outline/metrics/Unicode/OS/2/layout comparison was not repeated. The 2026-10-22 FontTools 4.61.0 inspection recorded above remains the evidence for that comparison; this local recheck is supplemental and does not establish final-font or official qualification.

## Issue #71 clean-build dependency provenance

**Decision and approval:** Accepted ADR-013 records the Debian snapshot,
hash-locked Python runtime/build wheelhouse, and source-bound local renderer
strategy. The issue owner authorized implementation in the direct task
instruction dated 2026-10-25. Issue comment
[6373327459](https://github.com/bjornefisk/ProjectChameleon/issues/71#issuecomment-6373327459)
requested approval; it did not grant it.

### Candidate build-input inventory

| Input | Exact candidate evidence |
| --- | --- |
| Base image | `python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5`; `linux/amd64` child `sha256:a8e0a3090316aed0b11037aac613aef32fb1747dcc1dcb5c0f6c727a0113a07f`; Python `3.11.11`. |
| Debian sources | Bookworm snapshot `https://snapshot.debian.org/archive/debian/20261025T143754Z/`; Bookworm Security snapshot `https://snapshot.debian.org/archive/debian-security/20261025T035125Z/`. Their signed InRelease SHA-256 values are `77737fa4b34f2693e982cc9ee35736816c35a7778fc2d326cc1bbf5b301fe1aa` and `5fdc0144562abd46f45083b48e1776898e234d93bbf6395b8147a53279d731db`. APT signature verification passed with the base image's `debian-archive-keyring=2023.3+deb12u1`. |
| Debian packages | Exact runtime roots: `libgl1=1.6.0-1`, `libegl1=1.6.0-1`, `libglib2.0-0=2.74.6-2+deb12u9`, and `fontconfig=2.14.1-4`. `apt/packages.lock` contains the 54-package new closure; `apt/packages.sha256` hashes all 54 downloaded archives. Build evidence reports 0 upgrades and compares the complete installed `dpkg-query` output. |
| Python runtime | `requirements.in` supplies 41 exact constraints. `requirements.lock` is 1,405 lines and SHA-256 `0386cc02d31ef271ed3ae68d8fc544727a273c8bf9dcb734dc309b87b3ac5b5f`; all selected distributions and wheels are hash-locked. |
| Renderer build | `renderer-build.lock` is 28 lines and SHA-256 `e4b17a17cd56763c0a8c5491cebd1136aa4dbb1645861b2141443f28df0ff6cf`; Hatchling and its PEP 517 closure are installed from the same local wheelhouse. |
| Renderer artifact | Upstream `cr-renderer` commit `a17e1fb9a732959dd6c21ae168d5ee09d74bd64f` has a verified GitHub signature and Apache-2.0 license. The source archive SHA-256 is `18e8bdf0c22d43516829c4a7028b4eb5953f8dc2359ad3fd50054384a2b6ef71` (116,458 bytes). The local wheel is `cr_renderer-0.1.0-py3-none-any.whl`, 15,950 bytes, SHA-256 `92b4005c5777d305151321760cfb32e0c8e91a7041ac74fabe630bcc2e06fda9`. Two independent `linux/amd64` builds using the current `packaging==24.2` build lock produced this same hash. |
| Generated wheelhouse | 46 wheels. `.wheelhouse/manifest.json` SHA-256 `5cf515d60e773784b601d71de099e29943ab9e4e513b064a29824103179f3728`; it records every wheel filename, size, SHA-256, and lock/manifest/base-image input digest. It is generated and ignored, not committed. |
| Schema and product inputs | Schema SHA-256 `d084eb524b7b0e683c9a31a63706ea4101ee0e3cd4a9a3b8218a59975fa55e41`. Dockerfile SHA-256 `50d7eb17777cf74777c151cc9c1b46b5905a7eb101c1bf2f68cfee46c93ca5ec`. Full lock-input fingerprints are in the adjacent manifests. |
| Native libraries | The four apt roots and their 54-package closure are exact; native imports and `ldd` closure are required in `.github/workflows/ci.yml`. The local arm64-host emulation is supplemental. |

The selected `check-valid-until=no` setting is limited to the immutable
security-snapshot source; APT signature verification and each `.deb` hash
check remain enabled. The Docker build checks all installed Debian packages
for a non-empty `/usr/share/doc/<package>/copyright`; the 159-package local
image closure had no missing notice files. The wheelhouse review found license
or notice files in all 46 wheels, including the renderer. The observed
license families include MIT/X11, BSD, Apache-2.0 (including LLVM exception),
MPL-2.0, PSF-2.0, Unlicense, and LGPL/GPL terms carried in Debian copyright
files. This records package notices and license metadata; it is not a legal
opinion or a claim that hashes alone establish license compatibility.

Packaged runtime assets and fonts:

```text
chameleon/brand_kit/assets/solstice_bg_gradient.png  7ebf18d2a0d4b487cdf30578e4d6123e59e81502d78e55087768bfc5a465faeb
chameleon/brand_kit/assets/solstice_bottle.png       a9bea75d9592cee51bd1ee56e043662091326c612fc8c208eee3872c216aa053
chameleon/brand_kit/assets/solstice_logo_lockup.png   3a443c106090e7b043d85d553280e464b313d893baebafe6765fd3df1022f049
chameleon/brand_kit/fonts/SolsticeSans-BoldItalic.ttf e47af214406befc181508cf7ff87b774a955a670f7a54d8563a9757d45b2167d
chameleon/brand_kit/fonts/SolsticeSans-Bold.ttf       609a215925701021b97578c71702bfc492882556ce05602b670aaa74a32a1156
chameleon/brand_kit/fonts/SolsticeSans-Italic.ttf     848a0433face0f273e313e4fdb3497a764f3c96b3b6670dffcc3cc38dcc83f2a
chameleon/brand_kit/fonts/SolsticeSans-Regular.ttf    4500567b25fc1af2983cee01c1e57e01a0108b8b3844c182936d14c7dec7f69c
chameleon/brand_kit/fonts/SolsticeSerif-Bold.ttf      837d42cc1b336364b69714c73288a0ec7ceded41c137d5f62943df5f0745551a
chameleon/brand_kit/fonts/SolsticeSerif-Italic.ttf    07526ca6ef70e5a7853abcdd614aeb62cdb958ed0cabc0f771f85094b4c67ccf
chameleon/brand_kit/fonts/SolsticeSerif-Regular.ttf   b7eb2a832ae91824a7c670469f4a4e0c4910a3ceedc1d31aad07ea2bc336d2a7
```

### Local verification (supplemental Darwin arm64)

- `make setup VENV_DIR=/tmp/chameleon-issue71-setup-fixed.JxX4Ms/venv PYTHON_BOOTSTRAP=python3.11` — created Python `3.11.14`; locked Pillow `11.1.0`, Skia `132.0b11`, and the local `cr-renderer 0.1.0` wheel imported from the venv.
- `make verify PYTHON_BOOTSTRAP=python3.11` — passed.
- `make test PYTHON=/tmp/chameleon-issue71-setup-fixed.JxX4Ms/venv/bin/python` — 280 repository tests, 48 review-capsule tests, 3 runtime-qualification tests, 1 dependency-preparation regression, and 3 font-provenance tests passed (335 total). The first setup smoke exposed that `Path.resolve()` followed the venv's Python symlink and installed outside the venv; the helper now preserves the requested interpreter path and a regression test covers it.
- `make prepare-dependencies PYTHON_BOOTSTRAP=python3.11` — verified the existing 46-wheel manifest against current lock inputs and hashes.
- `docker buildx build --platform linux/amd64 --load -t chameleon-issue71-candidate chameleon/` — passed after checking all 159 installed-package copyright files. Docker emitted its non-blocking `FromPlatformFlagConstDisallowed` warning. Loaded image ID `sha256:d266651ef2e013c0b46bea441624469fe3cd05640cc900895211b61c8648b263`, size `352840969` bytes.
- Local supplemental Docker smoke used isolated temporary input/output mounts; its ad hoc command line was not retained. All three samples returned `SUCCESS` and published JSON, PNG, and commit markers. The nine artifact hashes are recorded below. This was amd64 emulation on Darwin arm64, not native qualification.
- A malformed JSON input returned exit `1`, status `MALFORMED_INPUT`, and left the isolated output directory empty.
- An independent `linux/amd64` offline renderer rebuild installed `renderer-build.lock` from the local wheelhouse and reproduced the manifest wheel hash and size. Its ad hoc command line was not retained; the native CI build remains the qualification gate.

### Native amd64 qualification

The prior native run `39988562284` qualified the direct-pin candidate only and
is historical. Initial Issue #71 run
[40227253405](https://github.com/bjornefisk/ProjectChameleon/actions/runs/40227253405)
passed on locked candidate `84ed3b4fac95efd208de87383fdc9009e1a48cf8`, but the
workflow did not retain its generated SPDX SBOM.

Updated-head run
[40228417003](https://github.com/bjornefisk/ProjectChameleon/actions/runs/40228417003)
passed `Verify and test` on candidate
`a2b8543f78bd2504b8d1051621972fb7220e1bce` (merge ref
`27eee971346a0b5c6733053b00d91564d1d4820b`), on GitHub's Ubuntu 24.04.5
x86_64 runner. The `linux/amd64` image ID was
`sha256:de27cd36d36371c5fc6b571c58849ad068f8abb36bee738ff65524a6a571bfed`,
size `848681354` bytes.

All three offline samples returned `SUCCESS` and published JSON, PNG, and
commit-marker artifacts. The nine native artifact hashes matched the local
sample table below; repeated-run and clean-cache comparisons passed. Malformed
input returned `MALFORMED_INPUT`, exit `1`, and no output files. Offline
renderer imports and Skia/Pillow `ldd` closure passed without missing
libraries. The workflow's test stages passed: 280 repository tests, 48 review
capsule tests, 3 runtime-qualification tests, 1 dependency-preparation test,
3 font-provenance tests, and the separate native renderer-golden test.

The pinned Anchore action uploaded workflow artifact
`chameleon-stage1-sbom.spdx.json` (artifact ID `12611997130`, compressed size
`468444` bytes). The downloaded document is SPDX-2.3, name `chameleon-stage1`,
220 packages, 4,861 relationships, 3,614,257 bytes, SHA-256
`28eb3be04d8bdf5233595e8b752c94f6ea4392ea43aff598503c83efa8981268`;
the SHA matches the workflow's recorded SBOM digest.
PR-head run
[40229964417](https://github.com/bjornefisk/ProjectChameleon/actions/runs/40229964417)
passed `Verify and test` on `b004f609c70440a510ceae645b8ff5de66afb071`
using Ubuntu 24.04.5 x86_64. Its `linux/amd64` image ID was
`sha256:e4db4bc65599ba1086b391c45a9f2a6c1eda4739d3a712c7f0b27537b1257fb2`.
The uploaded SBOM artifact (`12612674286`) is SPDX-2.3 with 220 packages,
4,861 relationships, 3,614,257 bytes, and SHA-256
`75f9def29db2071372d1a7e2ea92fbadea9e1b99bfab073eded669341e796da1`.

Runner-pinned PR-head run
[40232041519](https://github.com/bjornefisk/ProjectChameleon/actions/runs/40232041519)
passed `Verify and test` on `9af20a3b1863b0ba25bcf74bb1f4f1e1d9ed63fa`,
using Ubuntu 24.04.5 x86_64 (`ubuntu-24.04`, image version `20261012.334.1`).
Its `linux/amd64` image ID was
`sha256:61d300a1aac034a03899640cd814489e7e9c4039a49c99a96ed8442aae8e1007`.
All three offline samples returned `SUCCESS`; malformed input returned
`MALFORMED_INPUT`, exit `1`, and no output files. Repeated-run and clean-cache
hashes matched; native imports and Skia/Pillow `ldd` closure passed.

The uploaded artifact `chameleon-stage1-sbom.spdx.json` (artifact ID
`12613273548`, compressed size `468492` bytes) is SPDX-2.3 for
`chameleon-stage1`, with 220 packages, 4,861 relationships, and 4,039 files.
Its document SHA-256 is
`dacf4aa18eb8572e3b6750fa76fc2b933ac9ec04bd689f7e17dfc9a52b8d56c0`;
the workflow artifact digest is
`69ca4b1ae3349f1a57f2bc65816ad40148ccc262f9f17f58e22a496ac9152923`.

All three downloaded SBOMs have distinct document hashes, but the 219
non-container package records and all 4,039 file-name/checksum pairs are
identical. The root container identity and 726 generated file SPDX identifiers
varied by run; these are per-build SBOM hashes, not a byte-reproducibility
claim.


GitHub's [runner-image migration notice #14748](https://github.com/actions/runner-images/issues/14748) states that `ubuntu-latest` is transitioning to Ubuntu 26 beginning October 19, 2026. CI is pinned to `ubuntu-24.04` for a stable qualification major version.


PR #80 is merged and Issue #71 is closed. The final required `Verify and test`
run 40233682826 passed. Cross-platform parity, organizer-held-out scoring,
organizer resource limits, and release qualification remain unverified.


Native runtime observation: Python `3.11.11` on Linux `x86_64`, exit `0`,
wall time `22.392221032` seconds, user CPU `21.950268` seconds, system CPU
`0.526766` seconds, maximum RSS `297016 KiB`, peak `3` procfs threads, and
`2` available CPUs. These are runner observations, not organizer limits.
Logs included Fontconfig, warning-only off-canvas self-check, and missing-asset
warnings; none were treated as hard-validation evidence. Full provenance
hashes and exact check details are in the
[Issue #71 run record](../.agents/runs/issue-71-clean-build-dependency-provenance-20261025.md).

### Accepted lock strategy

ADR-013 records the accepted durable decision. **OBSERVED, Debian Project,
retrieved 2026-10-25:** [snapshot.debian.org](https://snapshot.debian.org/)
documents historical archive sources; the selected URLs, signatures, hashes,
and expiry handling are pinned in the repository evidence files.
**OBSERVED, Python Packaging Authority pip source at tag `26.2.2`** (tag object
`147fd2284a1f3222683b4176269658a47a72de95`, target commit
`b3b696fe2122f2339d782517559bfade2cb6b879`, retrieved 2026-10-23):
[secure installs](https://raw.githubusercontent.com/pypa/pip/b3b696fe2122f2339d782517559bfade2cb6b879/docs/html/topics/secure-installs.md)
documents `--require-hashes`, `--only-binary=:all:`, and local `--no-deps`
installation. The selected strategy is recorded in ADR-013; the earlier Issue
comment 6373327459 is not approval evidence.

### Local sample artifact hashes

The following outputs were generated by the local supplemental emulation run above. Native runs `40228417003`, `40229964417`, and `40232041519` produced the same nine JSON/PNG/commit-marker hashes, and all three repeat/clean-cache comparisons passed:

| Artifact | SHA-256 |
| --- | --- |
| Level 1 JSON | `7b93fdfd44ad8e669c00aeae3a8e96931f85a761a60e67cc31d2bb02b10853b9` |
| Level 1 PNG | `172d23ca87020478d24568a603ba6f9deaf272629b59d73608789aca9789a85c` |
| Level 1 commit marker | `cf3a261e6a5ba4ee827063897f290776db60dd890e662a73dfc36d8d3998cd34` |
| Level 2 JSON | `3e26ef9e95df3f9b9f3fc9fa8149382962081531936e5f01480f5161e3b5f8f6` |
| Level 2 PNG | `bf24e67125529d96b65df1f049d3f4b11cd0fcc9e05a2c7a765a60c3e5952f99` |
| Level 2 commit marker | `62c8f1c6de62c79209900086b64139308e60bf2f5919496998a6d8a5c40002ce` |
| Level 3 JSON | `10c7b96bea147205da2ba24030f1b2d8970e46f83f76bccc67c9f6798b955fdd` |
| Level 3 PNG | `1cbe6edde1ee854439dda7e3eb1061a61964a1d4116bda0fc1fd9e90629fe6ff` |
| Level 3 commit marker | `19fe9a7e1d34d8188da678cc9d4e5cb3e2bf96a929efde1f6a9d4452a592b625` |

## Unverified or intentionally deferred

- **OBSERVED, 2026-10-20, commit `6c6bb21`:** GitHub Actions run [39353319577](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39353319577) stopped at `docker sbom chameleon-stage1 --format syft-json --output ...` because the runner provided no `docker sbom` command; native runtime, reproducibility, and closure steps were not reached. Disposition: use the pinned `anchore/sbom-action`/Syft path and rerun the workflow.
- **OBSERVED, 2026-10-20, commit `7f39a3e`:** GitHub Actions run [39481028806](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39481028806), job `118829322922`, completed the native `linux/amd64` qualification path. The loaded image was `linux/amd64`, ID `sha256:6c555cecec045651bcadc3d5f28215ff9a5b9dd9257e367e3fe5e26975642d4b`, size `886388964` bytes; the SPDX SBOM generated by pinned Syft `v1.42.3` was non-empty with SHA-256 `944833771af7e92d0bae7da85fe4924c54175ac1e2027c9dd3407b75acb9a0fc`. The offline (`--network none`) runtime report measured `13.690699821` seconds wall time, `13.256694` user and `0.51691` system CPU seconds, `307076 KiB` maximum RSS, peak `3` Linux threads from procfs, and `2` available CPUs on Python `3.11.11`/`x86_64`; return code `1` was expected because the mixed sample batch keeps Level 3 fail-closed as `INCOMPLETE_SEARCH` while Level 1/2 returned `SUCCESS` pairs. The native library `ldd` checks and offline `cr_renderer`/Skia imports passed with no `not found` dependencies. Repeated native and clean-cache runs passed artifact/symlink checks and produced the same committed sample hashes: Level 1 JSON `237a8a9eeeeae02ab954bf820fc0294b2501890097c390b3bb6c0c148d2744ba`, Level 1 PNG `71e0be9ea2ae55ab860100fed77ce870e1f531da8f74df05adb67414cf27cea0`, Level 2 JSON `3e26ef9e95df3f9b9f3fc9fa8149382962081531936e5f01480f5161e3b5f8f6`, and Level 2 PNG `bf24e67125529d96b65df1f049d3f4b11cd0fcc9e05a2c7a765a60c3e5952f99`. The packaged local assets were hashed as `solstice_bg_gradient.png=7ebf18d2a0d4b487cdf30578e4d6123e59e81502d78e55087768bfc5a465faeb`, `solstice_bottle.png=a9bea75d9592cee51bd1ee56e043662091326c612fc8c208eee3872c216aa053`, and `solstice_logo_lockup.png=3a443c106090e7b043d85d553280e464b313d893baebafe6765fd3df1022f049`; all seven packaged Solstice TTF hashes were recorded in the run log, proving local image/font loading without a runtime download.
- **OBSERVED, historical direct-pin candidate:** Native-amd64 run `39481028806` is evidence for that pinned image only; it is not qualification for Issue #71's locked candidate or organizer qualification. Cross-platform hash parity is not established. The 2026-10-19 arm64-host emulation evidence remains supplemental.
- **OBSERVED, supplemental, 2026-10-19:** Local arm64-host emulation produced expected Level 1/2 success and Level 3 `INCOMPLETE_SEARCH`, resolved Skia/Pillow `ldd` closure, and matching repeated/clean-cache hashes; it is not native-amd64 qualification.
- **OBSERVED, supplemental, 2026-10-19:** Final local loaded image provenance was a `linux/amd64` image with ID `sha256:178c0feecdfb3100fc5266d663d438ac655743b1a7cac744a79bbe4857050390`, size `303795243` bytes, and Syft JSON SBOM SHA-256 `da40711f9edc5635c51f10ac6e730bb19c4151a415ea9dbb3b7e67bf18039844`; this remains arm64-host evidence.
- **UNVERIFIED_EXTERNAL_FACT (production-font scope):** Exact final Adobe/Solstice production font files/source IDs, availability, written packaging/redistribution authorization, and disclosure permission have not been supplied or verified. Source: no exact production files or applicable written terms are present in the repository. Impact/disposition: defer production integration and release qualification; keep Issue #70 open as a production-release gate, not a blocker to repository-link-only submission.
- **OBSERVED / INFERRED (placeholder scope only):** The seven Lora/Poppins stand-in TTFs match the pinned starter-kit Git-blob SHA-1s and manifest SHA-256s; embedded face metadata, checked-sample glyph coverage, and both bundled OFL texts/hashes are verified for these exact files. Their OFL redistribution terms apply only to these placeholders and do not establish production-font rights.
- **UNVERIFIED_EXTERNAL_FACT (organizer scope):** No organizer response or official scoring protocol/result was received as of 2026-10-30. Official evaluator revision, score, rubric, thresholds, target catalogue, failure/result semantics, disclosure permission, and qualification remain unknown. Exact M5 Pro resource/model limits and Adobe deployment topology also remain unverified. Local tests, public fixtures, synthetic audits, and CI are internal engineering evidence only and do not establish organizer scoring or qualification. Keep Issue #69 open and blocked for official qualification claims; this is outside repository-link-only submission scope.
