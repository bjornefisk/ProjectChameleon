# Project Chameleon external dependency evidence

**Status:** Ratified evidence record for Stage 1 planning

This file applies source-driven development only to external libraries, platforms, and packaging. It does not decide internal product intent; those decisions are in `PROJECT_CONTRACT.md` and the ADRs.

**Revision note:** The native-amd64 measurements below are for the earlier commit `7f39a3e`, before Issue #61. They remain valid observations for that revision, not qualification evidence for the Issue #61 branch. Later native x86_64 CI run 39711973748 passed on PR #65's head commit `33f6fd9`; cross-platform parity and organizer-controlled qualification remain open in `STATUS.md`.

## Evidence matrix

| Topic | Detected state | Source-backed fact | Decision/pin | Required conformance test |
| --- | --- | --- | --- | --- |
| `cr-renderer` source | The old requirement installed the moving default branch. The observed `main` SHA is `a17e1fb9a732959dd6c21ae168d5ee09d74bd64f`; upstream package metadata says version `0.1.0`, Python `>=3.10`. | [commit API](https://api.github.com/repos/CyberAgentAILab/cr-renderer/commits/main), [commit](https://github.com/CyberAgentAILab/cr-renderer/commit/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f), [pyproject](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74f/pyproject.toml) | Pin the immutable SHA in `requirements.txt`. Treat future upgrades as a renderer ADR. | Clean amd64 install; record VCS direct URL and render a fixed PNG fixture. |
| Upstream renderer geometry | `CrelloV5Renderer` translates absolute `left/top`, rotates around the local center in degrees, draws images into the destination rectangle, and downsizes to `max_size`. | [renderer.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74f/src/cr_renderer/renderer.py) | Contract against the pinned source plus the local adapter. Do not assume intrinsic contain/cover or automatic wrapping in upstream. | Non-square image, 90°/non-right-angle rotation, alpha, canvas scaling, and deterministic PNG tests. |
| Upstream text | `lineMap` supplies line ranges; absent map becomes one line. Line origins use `line_index * fontSize * lineHeight`; glyph advances include letter spacing; alignment is applied inside width. `wordBreak` is not used by the render path. | [schema.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/schema.py), [text_utils.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74f/src/cr_renderer/text_utils.py) | Keep public Chameleon text unchanged; the adapter owns deterministic line-map generation. | Explicit two-line map, missing map, all alignments, spacing, style maps, and glyph-bound tests. |
| Local text adapter | The wrapper measures effective style spans, preserves code-point `[start,end)` runs, intersects UAX #29 clusters with UAX #14 opportunities, enforces explicit line/height limits, and rejects malformed or unbreakable text. | `chameleon/renderer/converter/wrap.py`, `convert.py`, `unicode_data.py` | Keep adapter behavior aligned with ADR-008 and the pinned renderer. | Boundary/style/spacing/height, Unicode property, non-breaking class, malformed-input, and glyph-bound tests. |
| Unicode text properties | The adapter's grapheme, Indic conjunct, line-break, general-category, and East Asian width decisions use generated Unicode 17.0.0 tables from the official UCD files. | [GraphemeBreakProperty.txt](https://www.unicode.org/Public/17.0.0/ucd/auxiliary/GraphemeBreakProperty.txt), [emoji-data.txt](https://www.unicode.org/Public/17.0.0/ucd/emoji/emoji-data.txt), [DerivedCoreProperties.txt](https://www.unicode.org/Public/17.0.0/ucd/DerivedCoreProperties.txt), [LineBreak.txt](https://www.unicode.org/Public/17.0.0/ucd/LineBreak.txt), [UnicodeData.txt](https://www.unicode.org/Public/17.0.0/ucd/UnicodeData.txt), [EastAsianWidth.txt](https://www.unicode.org/Public/17.0.0/ucd/EastAsianWidth.txt) | Keep tables versioned with the adapter; upgrade only with renderer conformance evidence. | UAX #29 cluster cases, UAX #14 GL/WJ/BA/punctuation cases, and repeated deterministic wrapping. |
| Renderer transitives | The selected upstream `uv.lock` recorded `datasets 3.2.0`, `pydantic 2.10.6`, `skia-python 132.0b11`, `Pillow 11.1.0`, and `numpy 2.2.2`; upstream project metadata supplies lower bounds only. | [upstream pyproject](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/pyproject.toml), [upstream lock](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74f/uv.lock) | Pin the compatibility baseline directly in `requirements.txt`; a full hash-locked wheelhouse remains follow-up work. | Fresh amd64 build, `pip freeze`, imports for every used symbol, local font load, and sample render. |
| Pillow | The prior requirement was `Pillow>=10.0`. Official support lists Python 3.11 for Pillow 10, 11, and 12. | [Pillow Python support](https://pillow.readthedocs.io/en/stable/installation/python-support.html) | Pin `Pillow==11.1.0` for parity with the selected renderer lock. | Decode all packaged assets; exercise RGBA conversion, LANCZOS contain/cover/fill, shape rasterization, placeholder, and PNG round-trip. |
| Skia Python binding | Skia was transitive and lower-bounded at `>=120.0b5`; the selected lock recorded `132.0b11`. | [skia-python 132.0b11](https://pypi.org/project/skia-python/132.0b11/), [Skia download/build](https://skia.org/docs/user/download/) | Pin `skia-python==132.0b11`; verify native libraries in the target image. | Import Skia, create a CPU surface, load each TTF, render text/image/rotation, encode PNG. |
| PNG golden runtime | Official image uses Python 3.11.11; native CI selects Python 3.11; persisted renderer and engine hashes bind Python 3.11, renderer revision, Pillow, Skia, and fonts. | [`chameleon/Dockerfile`](../chameleon/Dockerfile), [CI workflow](../.github/workflows/ci.yml), [`requirements.txt`](../chameleon/requirements.txt), [golden fixtures](../chameleon/tests/fixtures/) | Local setup defaults to `python3.11`; `make test` rejects another minor. PNG hashes remain per-OS/machine evidence, not universal parity. | Run renderer and engine hash cases in each recorded environment; preserve contract/artifact checks and fail on environment or hash drift. |
| Datasets/Pydantic | Both were transitive and lower-bounded by `cr-renderer`; the selected lock recorded `datasets==3.2.0` and `pydantic==2.10.6`. | [cr-renderer pyproject](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/pyproject.toml) and lock above | Pin the selected versions because the adapter uses `datasets` feature types and upstream Pydantic models. | Import `CrelloV5Renderer`, exercise the feature stub, and render with an empty and non-empty element list. |
| JSON Schema validator | No validator dependency existed in the starter. | [jsonschema Draft 2020-12 docs](https://python-jsonschema.readthedocs.io/en/stable/validate/) | Pin `jsonschema==4.23.0` for contract tests using `Draft202012Validator`. | Validate the schema itself, all sample sources, empty design, and negative structural cases. |
| Python JSON numeric ingress | `json.load` passes the original numeric token text to `parse_int` and `parse_float`; the default float path creates binary floats, and `parse_constant` handles non-standard `NaN`/`Infinity` tokens. | [Python 3.11 `json` documentation](https://docs.python.org/3.11/library/json.html#json.load) | Use `parse_int=int`, `parse_float=Decimal`, and a rejecting `parse_constant` hook before validation and geometry. | Runner-seam cases for finite decimal, exponent, integer, and non-finite-constant inputs; serialize mutable geometry/font-size values as finite integers while retaining only contract-approved immutable values. |
| OR-Tools CP-SAT | Absent from requirements, imports, and code; present only in proposed architecture. | [CP-SAT guide](https://developers.google.com/optimization/cp/cp_solver), [Python API](https://or-tools.github.io/docs/pdoc/ortools/sat/python/cp_model.html), [release metadata](https://pypi.org/pypi/ortools/9.15.6755/json) | Do not add it during ratification. If selected later, pin a release and test integer intervals, status paths, allowed overlaps, and rotated post-validation. | Tiny deterministic model plus solver-status and geometry-validator checks. |
| Docker platform | The starter forced `linux/amd64` but used a mutable base tag. Docker documents `--platform` selection and QEMU emulation for non-native builds; a `docker-container` Buildx builder does not automatically load its result into the local image store. | [Docker multi-platform builds](https://docs.docker.com/build/building/multi-platform/), [base-image pinning](https://docs.docker.com/build/building/best-practices/#pin-base-image-versions), [Buildx `--load`](https://docs.docker.com/reference/cli/docker/buildx/build/#load) | Keep a single amd64 scoring artifact. Pin `python:3.11.11-slim-bookworm` to the observed OCI index digest in `Dockerfile`; use `--load` for the local build-then-run smoke path; qualify the amd64 child digest during build. | Buildx amd64 build on Apple Silicon and native amd64; inspect `uname -m`, Python patch, wheel architecture, and sample PNG. |
| Python base image | `python:3.11-slim` was mutable. Docker Hub reports `3.11.11-slim-bookworm` manifest digest `sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5` and an amd64 child digest `sha256:a8e0a3090316aed0b11037aac613aef32fb1747dcc1dcb5c0f6c727a0113a07f`. | [Docker Hub image metadata](https://hub.docker.com/v2/repositories/library/python/tags/3.11.11-slim-bookworm) | Pin the manifest digest with an explicit `linux/amd64` target. Apt package versions are still not locked. | Record image digest/SBOM, Python version, native imports, and a clean rebuild result. |
| SBOM generation | The GitHub runner does not provide `docker sbom`; CI uses the pinned `anchore/sbom-action` commit `e22c389904149dbc22b58101806040fa8d37a610`, which embeds Syft `v1.42.3`, to scan the locally loaded image and emit SPDX JSON. | [sbom-action README](https://github.com/anchore/sbom-action/blob/e22c389904149dbc22b58101806040fa8d37a610/README.md), [action metadata](https://raw.githubusercontent.com/anchore/sbom-action/e22c389904149dbc22b58101806040fa8d37a610/action.yml), [pinned commit](https://github.com/anchore/sbom-action/commit/e22c389904149dbc22b58101806040fa8d37a610) | Pin the action commit and Syft version; keep artifact upload and dependency submission disabled for qualification. | Native amd64 workflow emits and hashes a non-empty SPDX JSON image SBOM without runtime network access. |
| Runtime qualification harness | `scripts/qualify_runtime.py` records child wall time, CPU time, maximum RSS with units, Linux peak observed child-thread count from `/proc/<pid>/status`, return code, and platform metadata; it atomically writes the JSON report. CI runs it inside the pinned image with `--network none`, records image size and packaged asset/font hashes, checks native-library `ldd` closure, validates the report and artifact set, and compares repeated and clean-cache sample artifact hashes. | Repository script and `.github/workflows/ci.yml` | Record observations without converting organizer-controlled resource limits into hard runtime gates. | Native amd64 CI run; report schema and expected statuses; repeat hashes; clean-cache image run; image-size, CPU, RSS, thread, latency, asset/font, and native-library logs. |
| Font loading | The project scans local TTF/OTF files and injects bytes into private `FontManager._fonts`; upstream default construction can download font data. | [upstream fonts.py](https://raw.githubusercontent.com/CyberAgentAILab/cr-renderer/a17e1fb9a732959dd6c21ae168d5ee09d74bd64f/src/cr_renderer/fonts.py) | Keep fonts in the image and use explicit local loading. Treat private-manager integration as revision-sensitive. | Hash every declared font, verify family/weight/style lookup, unknown-face failure behavior, and glyph advances. |
| Offline Hugging Face behavior | `datasets[vision]` is transitive; no model or weights are present. | [Hugging Face offline variables](https://huggingface.co/docs/huggingface_hub/main/package_reference/environment_variables#hfhuboffline) | Stage 1 has no model dependency. Future model work must use immutable local artifacts and offline controls. | Empty caches + `HF_HUB_OFFLINE=1` + `--network none`; audit for attempted downloads. |
| Adobe Express add-on | No manifest, JS package graph, or add-on source exists. | [Add-on architecture](https://developer.adobe.com/express/add-ons/docs/guides/learn/platform-concepts/architecture), [UI SDK](https://developer.adobe.com/express/add-ons/docs/references/addonsdk/), [Document APIs](https://developer.adobe.com/express/add-ons/docs/references/document-sandbox/document-apis/), [Manifest v2](https://developer.adobe.com/express/add-ons/docs/references/manifest/) | Finale-only. When implemented, use the documented iframe/UI and document-sandbox split, manifest v2/API 1, and a separate npm lock. | Manifest, SDK readiness, sandbox/UI proxy, permissions, serialization, and no experimental API in release. |
| Adobe fonts | Stage 1 uses packaged TTF bytes, not Express document fonts. | [Express font API](https://developer.adobe.com/express/add-ons/docs/references/document-sandbox/document-apis/classes/fonts), [text guide](https://developer.adobe.com/express/add-ons/docs/guides/learn/how-to/use-text) | Do not promise Stage 1/Express metric parity or silent font substitution. | Resolve exact PostScript faces in entitled/unentitled accounts before finale typography claims. |
| Challenge hardware/model limits | Rules name Apple M5 Pro and leave CPU/RAM/disk/GPU and model allowlist/size unresolved. No model runtime or weights are in the repository. | Repository facts: `chameleon/RULES.md`; external platform docs cannot establish organizer limits. | Keep these as open external blockers; do not invent limits. | Await organizer specification, then add resource and deterministic-runtime tests. |

## Issue #70 packaged-font provenance and redistribution (evidence date: 2026-10-22)

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
## Issue #71 clean-build dependency provenance

`PR-74-build-provenance-inventory`. The source-input hashes were collected at
source revision `2548c82`; the evidence record was committed at PR head
`de935eb`. These records bind repository inputs without claiming
native-amd64 qualification.

### Current release-candidate input inventory

| Input | Observed value | Evidence boundary |
| --- | --- | --- |
| Base image | `python:3.11.11-slim-bookworm@sha256:081075da77b2b55c23c088251026fb69a7b2bf92471e491ff5fd75c192fd38e5` | Manifest digest is pinned; amd64 child digest requires candidate qualification. |
| Apt/build packages | `git`, `libgl1`, `libegl1`, `libglib2.0-0`, `fontconfig` | Names are declared in `chameleon/Dockerfile`; apt versions are unpinned. |
| Python runtime | Python `3.11.11` base image; CI selects Python `3.11` | Native CI observed Python `3.11.11`; complete wheel closure remains unresolved. |
| Direct Python requirements | Pillow `11.1.0`; datasets `3.2.0`; pydantic `2.10.6`; skia-python `132.0b11`; jsonschema `4.23.0` | Direct versions are pinned; no complete hash-locked wheelhouse is committed. |
| Renderer | `cr-renderer` commit `a17e1fb9a732959dd6c21ae168d5ee09d74bd64f` | VCS revision is immutable; native import and library closure remain run evidence. |
| Source inputs | Dockerfile `735b1d7f102874045c9f35afaa98d9dd439eb2b4e8d1a7ef6a2da5953cad39b2`; requirements `432fc158c299c37e15b52e0464401df62f72d786aa7af6e4086fc7de73209a1b`; schema `d084eb524b7b0e683c9a31a63706ea4101ee0e3cd4a9a3b8218a59975fa55e41` | Hashes bind this inventory to the checked-out source revision. |
| Native-library path | Skia and Pillow are checked with offline imports and `ldd` in `.github/workflows/ci.yml` | Native CI run `39981979377` passed imports and `ldd` with no `not found`; local emulation remains supplemental. |

Packaged runtime assets were hashed with the repository paths:

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

**OBSERVED:** The inventory was generated with `shasum -a 256` for source
files and sorted `find` output for packaged assets and fonts. Runtime network
remains disabled by `HF_HUB_OFFLINE=1`, `HF_HUB_DISABLE_TELEMETRY=1`, and the
CI `docker run --network none` path.

### Native amd64 CI qualification evidence

**OBSERVED, 2026-10-23:** Required GitHub Actions run
[39981979377](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39981979377),
job `120511316262`, passed for PR #74. The workflow tested merge ref
`cc4670e5cd2c02d5f766d15f54f7f99cbb2a762f`, which includes branch head
`779f4fc37790bd7e939cfc8bb95c1be365e315a1`.

- Native platform: Linux `x86_64`, Python `3.11.11`.
- Image: `sha256:2a128ecda7a70ce599ea48566c5512dae1b389bffc7d50b43aecdb82fec43572`,
  `linux/amd64`, `896530824` bytes.
- SBOM: non-empty SPDX output from pinned Syft `v1.42.3`, SHA-256
  `81efac5640b2592ad798f90565866d54196295a4ace251cccc2ffd6ec454c9aa`.
- Offline native smoke: all three samples returned `SUCCESS`; JSON, PNG, and
  commit-marker files were present.
- Repeated and clean-cache artifact hashes matched.
- Runtime: return code `0`, elapsed `17.95671395200003` seconds, maximum RSS
  `314092 KiB`, peak `3` procfs threads, and `2` available CPUs.
- Native `cr_renderer`/`skia` imports and Skia/Pillow `ldd` closure passed with
  no `not found` entries.

The run establishes native amd64 evidence for this candidate, not organizer
qualification. Apt-version closure, complete wheelhouse hashes,
cross-platform parity, and the reviewed package-lock decision remain open.

Native sample artifacts were:

| Artifact | SHA-256 |
| --- | --- |
| Level 1 JSON | `7b93fdfd44ad8e669c00aeae3a8e96931f85a761a60e67cc31d2bb02b10853b9` |
| Level 1 PNG | `172d23ca87020478d24568a603ba6f9deaf272629b59d73608789aca9789a85c` |
| Level 2 JSON | `3e26ef9e95df3f9b9f3fc9fa8149382962081531936e5f01480f5161e3b5f8f6` |
| Level 2 PNG | `bf24e67125529d96b65df1f049d3f4b11cd0fcc9e05a2c7a765a60c3e5952f99` |
| Level 3 JSON | `10c7b96bea147205da2ba24030f1b2d8970e46f83f76bccc67c9f6798b955fdd` |
| Level 3 PNG | `1cbe6edde1ee854439dda7e3eb1061a61964a1d4116bda0fc1fd9e90629fe6ff` |

## Unverified or intentionally deferred

- **OBSERVED, 2026-10-20, commit `6c6bb21`:** GitHub Actions run [39353319577](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39353319577) stopped at `docker sbom chameleon-stage1 --format syft-json --output ...` because the runner provided no `docker sbom` command; native runtime, reproducibility, and closure steps were not reached. Disposition: use the pinned `anchore/sbom-action`/Syft path and rerun the workflow.
- **OBSERVED, 2026-10-20, commit `7f39a3e`:** GitHub Actions run [39481028806](https://github.com/bjornefisk/ProjectChameleon/actions/runs/39481028806), job `118829322922`, completed the native `linux/amd64` qualification path. The loaded image was `linux/amd64`, ID `sha256:6c555cecec045651bcadc3d5f28215ff9a5b9dd9257e367e3fe5e26975642d4b`, size `886388964` bytes; the SPDX SBOM generated by pinned Syft `v1.42.3` was non-empty with SHA-256 `944833771af7e92d0bae7da85fe4924c54175ac1e2027c9dd3407b75acb9a0fc`. The offline (`--network none`) runtime report measured `13.690699821` seconds wall time, `13.256694` user and `0.51691` system CPU seconds, `307076 KiB` maximum RSS, peak `3` Linux threads from procfs, and `2` available CPUs on Python `3.11.11`/`x86_64`; return code `1` was expected because the mixed sample batch keeps Level 3 fail-closed as `INCOMPLETE_SEARCH` while Level 1/2 returned `SUCCESS` pairs. The native library `ldd` checks and offline `cr_renderer`/Skia imports passed with no `not found` dependencies. Repeated native and clean-cache runs passed artifact/symlink checks and produced the same committed sample hashes: Level 1 JSON `237a8a9eeeeae02ab954bf820fc0294b2501890097c390b3bb6c0c148d2744ba`, Level 1 PNG `71e0be9ea2ae55ab860100fed77ce870e1f531da8f74df05adb67414cf27cea0`, Level 2 JSON `3e26ef9e95df3f9b9f3fc9fa8149382962081531936e5f01480f5161e3b5f8f6`, and Level 2 PNG `bf24e67125529d96b65df1f049d3f4b11cd0fcc9e05a2c7a765a60c3e5952f99`. The packaged local assets were hashed as `solstice_bg_gradient.png=7ebf18d2a0d4b487cdf30578e4d6123e59e81502d78e55087768bfc5a465faeb`, `solstice_bottle.png=a9bea75d9592cee51bd1ee56e043662091326c612fc8c208eee3872c216aa053`, and `solstice_logo_lockup.png=3a443c106090e7b043d85d553280e464b313d893baebafe6765fd3df1022f049`; all seven packaged Solstice TTF hashes were recorded in the run log, proving local image/font loading without a runtime download.
- **UNVERIFIED:** The successful run is native-amd64 evidence for the pinned image and current runner, not a complete organizer qualification. Cross-platform hash parity is not established. The workflow compares repeated and clean-cache runs of the same native `linux/amd64` image; the 2026-10-19 arm64-host emulation evidence remains supplemental and is not a native-amd64 or cross-platform parity claim.
- **OBSERVED, supplemental, 2026-10-19:** Local arm64-host emulation produced expected Level 1/2 success and Level 3 `INCOMPLETE_SEARCH`, resolved Skia/Pillow `ldd` closure, and matching repeated/clean-cache hashes; it is not native-amd64 qualification.
- **OBSERVED, supplemental, 2026-10-19:** Final local loaded image provenance was a `linux/amd64` image with ID `sha256:178c0feecdfb3100fc5266d663d438ac655743b1a7cac744a79bbe4857050390`, size `303795243` bytes, and Syft JSON SBOM SHA-256 `da40711f9edc5635c51f10ac6e730bb19c4151a415ea9dbb3b7e67bf18039844`; this remains arm64-host evidence.
- **UNVERIFIED_EXTERNAL_FACT, source-input revision `2548c82`:** Apt package versions
  and a complete hash-locked transitive wheelhouse remain unverified. The
  Dockerfile declares `git`, `libgl1`, `libegl1`, `libglib2.0-0`, and
  `fontconfig` without apt versions. The direct requirements are pinned, but
  pip still resolves a complete wheel set at build time. Impact: clean-cache
  builds do not prove byte-identical dependency resolution. Disposition:
  approve a lock strategy through normal dependency review before changing
  dependency or packaging inputs.
- **UNVERIFIED_EXTERNAL_FACT:** Final Adobe/Solstice production font availability remains unverified; source: final-stage Adobe font entitlement and production brand files are not present in the repository; impact: this evidence covers only the exact packaged Lora/Poppins placeholders; disposition: do not infer production-font authorization or substitute fonts.
- **UNVERIFIED_EXTERNAL_FACT:** Font embedded metadata, glyph coverage, licensing, and redistribution rights remain unverified; source: the external font/dependency records cited above; impact: release licensing and final-font parity remain open; disposition: no font substitution or licensing claim is added.
- **UNVERIFIED_EXTERNAL_FACT:** Exact organizer CPU/RAM/disk/GPU limits, model allowlist/size, official scoring thresholds, and Adobe deployment topology remain unverified; source: `chameleon/RULES.md` and the challenge brief at repository revision `6c6bb21` (2026-10-20); impact: measurements are observations, not hard qualification ceilings; disposition: do not invent limits or add runtime gates.
