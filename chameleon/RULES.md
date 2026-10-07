# CHAMELEON — Submission Rules & Clarifications

*Adobe North America Hackathon 2026 — Pilot Edition*

*This supplements the main challenge brief. For this repository's ratified Stage 1 behavior, `Docs/PROJECT_CONTRACT.md` and Accepted ADRs are authoritative; this file records organizer-facing scoring restrictions.*

---

## Performance

**Latency is not a disqualifying concern.** There is no hard execution-time limit for stage one. A faster engine is preferred, all else equal — "speed and reliability" is a rubric row — but a slower, higher-quality result will not be thrown out just for being slower. Optimize for quality first.

## What gets compared during scoring

Both artifacts your engine produces are evaluated, not just one:

- **The output JSON itself** — checked structurally: same element `id`s and order as the source (nothing added or removed), required fields present, rotated active-foreground bounds inside the target except the documented background/source-bleed exceptions, images kept in proportion, and so on.
- **The rendered PNG** — your output JSON run through the pinned project renderer, then scored by the AI evaluator against the rubric.

A submission with plausible-looking JSON that doesn't actually render legibly doesn't get credit for the JSON, and a rendered image that happens to look fine despite a broken or dishonest JSON doesn't get credit for the image. Both are checked.

## Models and fine-tuning

If an engine relies on a fine-tuned or adapted model — for example, a LoRA adapter on top of an open base model — **the weights must be publicly accessible**: hosted somewhere judges can pull them (e.g. a public Hugging Face repo), not kept private or shared ad hoc. This repository currently has no model runtime or weights; the final model allowlist and size limit remain organizer-controlled TBD facts.


## Evaluation hardware

The rules currently name **Apple M5 Pro** as the reference machine. Exact CPU/RAM/disk/GPU limits are still TBD and are not inferred by this repository.

Stage-one scoring is expected to use that reference machine. Build and test within the published budget once the exact limits are supplied; do not infer a resource target from the product name alone.

## Target canvas sizes

Target sizes used in scoring are drawn from a fixed catalogue of common real-world formats, described the way a designer would — e.g. "Instagram Post," "YouTube Thumbnail" — alongside their exact resolution and aspect ratio. This catalogue is one of the "fixed materials" you're allowed to rely on (main brief, Section 5): you can safely assume target sizes will look like real platform formats, not arbitrary rectangles, even though the *specific* hidden targets used at scoring time are ones you won't have seen in advance.

## Adaptive typography and copy

Changing **font size** to help text fit is part of the Stage 1 resize problem. Stage 1 keeps the text string, font family, weight, style, color, line height, letter spacing, and style runs fixed. The project contract defines adapter-owned line generation and renderer-matched measurement.

Changing font family or rewriting/shortening text is outside Stage 1. It may be explored as an explicit finale interaction, but it must not appear in a contract-conforming Stage 1 response.

## Disqualifying: regenerating image content

**Do not regenerate, redraw, or replace the pixel content of any asset — including with generative AI — even for a background or a minor decorative element.** The engine repositions and resizes the elements it's given; it does not invent new imagery. This is the same "no image generation" principle stated throughout the main brief, called out here plainly because it is a **disqualifying violation, not a point deduction**.

If you're ever unsure whether something you're doing counts as "regenerating" versus "resizing," ask before you submit.
