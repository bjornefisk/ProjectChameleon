# Objective evaluation metrics and aesthetic alignment

> **Authority Notice:** This document defines internal optimization proxies for candidate ranking. The binding Stage 1 behavioral contract is ratified in [PROJECT_CONTRACT.md](PROJECT_CONTRACT.md) and Accepted [ADRs](DECISIONS/). In any conflict, the contract and ADRs govern.

Stage 1 produces a design JSON and a rendered PNG on success. Structural checks apply to the JSON, and a separate evaluator may judge the rendered composition. The metrics in this document are internal comparison proxies, not the official rubric, not ratified fixed-point scales or weights, and not substitutes for the contract validator.

## Scoring pipeline

```text
Source-aware layout candidates
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│              VALIDATION AND SOFT SCORING               │
│                                                        │
│  Hard structural gates (post-serialization):            │
│    - exact element ids, count, order, types, fixed fields│
│    - rotated AABB containment (with source bleed rule)   │
│    - exact foreground image ratio preservation           │
│    - rigid group integrity (no child drift)              │
│    - zero new positive-area collisions (source-separated)│
│    - actual rendered glyph bounds inside text box        │
│    - missing asset preservation; no generated pixels     │
│                                                        │
│  Soft candidate ranking terms (hard-valid only):        │
│    - rendered readability & contrast:  Rea -> 1         │
│    - shared alignment:                 Ali -> 0         │
│    - visual balance:                   Bal -> 1         │
│    - busy-image occlusion:             Occ -> 0         │
│    - source overlap preservation                        │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
                 Rank only hard-valid candidates
```

An invalid candidate is rejected before it receives a soft score. A high score cannot compensate for a missing element, an off-canvas rotated bound, an altered fixed property, or generated image content.

## 1. Geometric validity

The structural validity gate checks exact identity and rotated containment:

$$
\text{Val} =
\mathbb{I}\left[
\operatorname{ids}(\mathcal{D}_{\text{tgt}})
=
\operatorname{ids}(\mathcal{D}_{\text{src}})
\land
\forall e_i,\ \operatorname{AABB}_{\theta_i}(e_i)
\subseteq
\mathcal{C}_{\text{tgt}}
\right]
$$

The check does not impose an arbitrary minimum area. Zero-size source elements and line shapes remain records and are handled without division by zero. The engine must not create zero-size geometry to remove an element from the composition.

## 2. Source-aware overlap

Let $\mathcal{P}_{\text{new}}$ contain element pairs that did not overlap in the source and are not permitted background or container relationships. Let $\mathcal{O}_{\text{src}}$ contain intentional source overlaps.

$$
\text{Ove} =
\frac{1}{|\mathcal{P}_{\text{new}}|}
\sum_{(e_i,e_j)\in\mathcal{P}_{\text{new}}}
\frac{\operatorname{Area}(e_i\cap e_j)}
{\max(\min(\operatorname{Area}(e_i),\operatorname{Area}(e_j)), \epsilon)}
$$

If $\mathcal{P}_{\text{new}}$ is empty, define $\text{Ove}=0$. The metric uses rotated bounds for geometry checks. A source-intended overlap is excluded only when its relationship remains intact. Text on a busy image remains a separate readability failure.

## 3. Alignment

Alignment measures the distance from each element to the closest shared axis among other independent elements or rigid groups. The candidate can use left, center, right, top, middle, and bottom axes:

$$
\text{Ali} =
\frac{1}{|\mathcal{E}|}
\sum_i
\min_{j\ne i}
\min_k
\frac{|A_k(e_i)-A_k(e_j)|}
{\max(W_{\text{tgt}},H_{\text{tgt}})}
$$

The term is a preference. It must not pull a group apart or create a new overlap just to improve an axis match.

## 4. Canvas balance

Estimate visual mass from non-background element area. When the total mass is positive, compute:

$$
\bar{x} =
\frac{\sum_i w_i h_i (x_i+w_i/2)}
{\sum_i w_i h_i}
\qquad
\bar{y} =
\frac{\sum_i w_i h_i (y_i+h_i/2)}
{\sum_i w_i h_i}
$$

Then:

$$
\text{Bal} =
1 -
\frac{
\sqrt{(\bar{x}-W_{\text{tgt}}/2)^2+
(\bar{y}-H_{\text{tgt}}/2)^2}
}{
\frac{1}{2}\sqrt{W_{\text{tgt}}^2+H_{\text{tgt}}^2}
}
$$

For a scene with no positive-area foreground mass, balance is neutral rather than a divide-by-zero failure. Balance is a soft signal, not a requirement to center every design.

## 5. Busy-image occlusion

The occlusion term measures text over a busy image only when the source did not establish a readable overlay:

$$
\text{Occ} =
\frac{
\sum_{e_k\in\mathcal{E}_{\text{text}}}
\operatorname{Area}\left(e_k\cap
\mathcal{B}_{\text{busy}}\right)
}{
\max(\operatorname{Area}(\mathcal{B}_{\text{busy}}),\epsilon)
}
$$

Text on a source button or intentional text container is not penalized as an accidental collision. Actual background pixels, opacity, and source overlays determine whether the text is readable.

## 6. Rendered readability and contrast

Readability combines the measured font-size floor with contrast against the rendered pixels below the actual glyph bounds:

$$
\text{Rea} =
\frac{1}{|\mathcal{E}_{\text{text}}|}
\sum_{e_k\in\mathcal{E}_{\text{text}}}
\mathbb{I}(s_k\ge s_{\min})
\cdot
\min\left(
1,
\frac{\operatorname{ContrastRatio}
(e_k,\mathcal{B}_{\text{rendered}}(e_k))}
{4.5}
\right)
$$

Use a neutral value when a design contains no text. The floor is roughly $10$ px unless the source is already smaller. The source hierarchy is scored by relative ordering and scale, not by a fixed ratio invented for all designs.

The values in this document are internal comparison terms. They are not claims about the grader's exact thresholds. Structural JSON checks and the rendered PNG remain the actual submission artifacts.

## Metric summary

| Metric | Definition | Candidate use | Hard gate |
| --- | --- | --- | --- |
| Structural validity ($\text{Val}$) | Exact IDs, count, order, types, fixed fields, rotated containment, image ratios, groups, no new collisions, glyph bounds | Reject invalid candidates | Yes (hard gate) |
| Readability ($\text{Rea}$) | Measured font size above floor and contrast against rendered background | Maximize softly | Soft ranking term |
| Alignment ($\text{Ali}$) | Distance to shared axes without breaking groups | Minimize softly | Soft ranking term |
| Balance ($\text{Bal}$) | Visual-mass offset from the canvas center | Maximize softly | Soft ranking term |
| Occlusion ($\text{Occ}$) | Text over busy imagery without a source treatment | Minimize softly | Soft ranking term |
| Overlap proxy ($\text{Ove}$) | Diagnostic estimate of unintended overlap among source-separated pairs | Optional diagnostic only | The validator's serialized positive-area overlap rule is the hard gate |
