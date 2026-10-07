# Interactive finale architecture and Adobe Express add-on integration

> **Authority Notice:** This document describes Stage 2 finale exploratory architecture only. The binding Stage 1 behavioral contract is ratified in [PROJECT_CONTRACT.md](PROJECT_CONTRACT.md) and Accepted [ADRs](DECISIONS/) (specifically [ADR-005](DECISIONS/ADR-005-separate-stage-1-from-finale.md)). Stage 1 remains an autonomous offline engine; finale controls are never engine inputs.

The Adobe Express add-on is a Stage 2 product layer around the Stage 1 retargeting engine. Stage 1 remains an offline, identity-preserving resize service. It cannot shed elements, rewrite copy, change fixed font attributes, hide records, or generate image content.

The add-on can expose controls that are deliberately outside the automated scoring contract: candidate selection, manual pinning, and exploratory alternatives. Any Stage 1 candidate shown in the add-on still has to satisfy the same JSON and rendered-PNG rules.

## Add-on architecture

```text
Express canvas document state and target selection
                      │
                      ▼
┌────────────────────────────────────────────────────────┐
│              ADOBE EXPRESS ADD-ON FRONTEND             │
│                                                        │
│  Finale controls:                                      │
│    - Candidate carousel                                │
│    - Spatial locking and pinning                       │
│    - Preview and user comparison                        │
│    - Separate exploratory copy or visibility controls  │
└──────────────────────────┬─────────────────────────────┘
                           │ (Local HTTP service via localhost / Wasm)
                           ▼
┌────────────────────────────────────────────────────────┐
│                 RETARGETING CORE ENGINE                │
│                                                        │
│  Stage 1 contract:                                     │
│    - Same element ids and count                         │
│    - Fixed text and visual attributes                   │
│    - Source-aware overlap and group constraints          │
│    - Hard validation before candidate ranking            │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
              Live rendered previews on Express canvas
```

## Multi-candidate hypotheses

A single valid layout may not be the strongest visual result. The engine can generate several candidates by changing soft objective weights while keeping the hard contract fixed:

$$
J(\mathcal{D}) =
\alpha \cdot \text{Scale}_{\text{hero}}
+ \beta \cdot \text{Scale}_{\text{text}}
+ \gamma \cdot \text{Bal}_{\text{canvas}}
$$

Candidate weights can favor hero scale, copy scale, or a balanced result. The weights affect ranking and slot preferences. They cannot permit an off-canvas bound, a new collision, a changed fixed property, or a missing element.

## Spatial pinning and semantic locking

A finale user may pin a logo or focal point to a chosen position. The add-on passes those values as extra constraints:

$$
x_k^{\text{tgt}} = X_{\text{pinned}}, \quad
y_k^{\text{tgt}} = Y_{\text{pinned}}
$$

Width and height remain subject to image-ratio and text-geometry rules. If a pin makes a valid layout impossible, the add-on should show that the choice cannot be satisfied rather than silently breaking the Stage 1 contract.

## Exploratory element shedding

Small formats can motivate a finale feature that lets a designer explore a reduced composition. That feature is not part of Stage 1. The Stage 1 engine must return every source element and must not set visibility, opacity, width, or height to zero.

If the finale presents a reduced preview, it must be treated as a separate user-controlled composition or an explicit future contract. It must not be mislabeled as a valid Stage 1 output.

## Context-aware copy adaptation

Copy changes are outside Stage 1. A finale prototype may suggest shorter alternatives in a separate user action, but the submitted Stage 1 layout keeps the source string, font family, weight, style, color, and style runs unchanged. The same separation applies to any experimental font substitution.

## Add-on capability summary

| Functional capability | Stage 1 status | Finale use | Constraint |
| --- | --- | --- | --- |
| Multi-candidate carousel | Internal candidates are allowed | Show valid alternatives for selection | Every shown Stage 1 candidate passes hard validation |
| Spatial pinning and locking | Not part of the autonomous input contract | Let a user steer a layout | Reject impossible pins instead of breaking constraints |
| Exploratory element shedding | Not allowed | Show a separate reduced composition | Never hide or zero an element in Stage 1 output |
| Adaptive copy revision | Not allowed | Suggest user-approved alternatives | Never change Stage 1 text content |
| Image regeneration | Disqualifying | Not a supported finale direction | Reuse the supplied pixels |
