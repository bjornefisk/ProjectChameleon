# Issue #70 production-font licensing research

**Date:** 2026-10-23
**Issue:** #70
**Branch:** `fix/issue-70-production-font-authorization`
**Scope:** authoritative licensing boundary for final Adobe/Solstice font files

## Observed sources

- Adobe Fonts, **Font licensing FAQs**, retrieved 2026-10-23:
  https://helpx.adobe.com/fonts/web/font-licensing/font-licensing.html
  - Adobe says its FAQ applies to fonts added through an Adobe account.
  - Adobe says Adobe Fonts Terms do not permit copying or moving font files to another user or computer.
  - Adobe says server installation and customer-created content require an appropriate license from the foundry or an authorized reseller.
- Adobe Fonts, **Packaging font files**, retrieved 2026-10-23:
  https://helpx.adobe.com/fonts/web/getting-and-using-fonts/package-font-files.html
  - Adobe says licensing terms vary by EULA and many licenses do not allow sending font files to third parties.
  - Adobe says the Adobe Fonts Terms do not allow copying or moving font files.

## Interpretation boundary

These sources establish why final production font authorization must be explicit. They do not identify the exact Adobe/Solstice files, grant this repository a license, or replace a written owner/foundry authorization.

The checked-in files remain the exact Lora/Poppins-derived placeholder files documented in `Docs/DEPENDENCY_EVIDENCE.md`. Their OFL evidence is separate from Adobe Fonts licensing and does not authorize future production files.

## Result

- No production font files changed.
- No font family substitution or runtime download was added.
- Issue #70 remains blocked on written authorization or an authoritative production-font direction covering the exact files, scope, and redistribution path.
- Do not close the issue from this research alone.

## Verification

- Source pages retrieved successfully on 2026-10-23.
- Existing `scripts/verify_font_provenance.py` and focused font tests remain the verification path for checked-in files.
