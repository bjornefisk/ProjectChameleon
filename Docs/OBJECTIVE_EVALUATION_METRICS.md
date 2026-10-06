# Objective evaluation metrics and aesthetic alignment

Stage 1 produces two scored artifacts: the output JSON and the rendered PNG. Structural checks apply to the JSON. A separate evaluator judges the rendered composition. The metrics in this document are internal proxies for candidate ranking, not the official rubric.

## Scoring pipeline

```text
Source-aware layout candidates
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│              VALIDATION AND SOFT SCORING               │
│                                                        │
│  Hard structural gates:                                │
│    - exact element ids and count                      │
│    - rotated bounds inside the target canvas           │
│    - image ratio and fixed-property preservation       │
│                                                        │
│  Source-aware quality terms:                           │
│    - unintended overlap:    Ove -> 0                  │
│    - alignment:             Ali -> 0                  │
│    - balance:               Bal -> 1                  │
│    - busy-image occlusion:  Occ -> 0                  │
│    - rendered readability:  Rea -> 1                  │
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
| Validity ($\text{Val}$) | Exact ids and count plus rotated containment | Reject invalid candidates | Yes |
| Overlap ($\text{Ove}$) | Unintended intersection among source-separated pairs | Minimize | Yes for new collisions |
| Alignment ($\text{Ali}$) | Distance to shared axes without breaking groups | Minimize | No |
| Balance ($\text{Bal}$) | Visual-mass offset from the canvas center | Maximize softly | No |
| Occlusion ($\text{Occ}$) | Text over busy imagery without a source treatment | Minimize | Readability gate |
| Readability ($\text{Rea}$) | Measured size and contrast under rendered glyphs | Maximize | Text must remain usable |
