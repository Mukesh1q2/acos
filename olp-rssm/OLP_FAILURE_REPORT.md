# OLP Phase 5 — Failure Report

> **Program**: OLP Phase 5 — RSSM Integration
> **Date**: 2026-06-12
> **This document records all failures honestly. No rescue attempts.**

---

## Summary

**OLP FAILED in RSSM.** Not marginally — dramatically.

Of the 5 hypotheses tested:
- 4 FAILED
- 1 PARTIALLY_PROVEN (marginal, not unique to OLP)

The most damaging finding: **OLP alone produces 2.2× worse prediction error than vanilla RSSM.**

---

## Failure 1: Prediction Degradation

**What was hoped**: OLP's structured latent space would improve prediction accuracy by providing more stable representations for the RSSM's recurrent dynamics.

**What happened**: OLP alone (QR projection, no KL) produced prediction MSE of 0.089, compared to vanilla RSSM's 0.040. This is a **120% increase in prediction error**.

**Root cause**: The St(8,4) Stiefel manifold has only K=4 orthogonal degrees of freedom. The GRU that processes the stochastic state receives a 32-dimensional input, but only 4 directions can vary independently. This creates an extreme information bottleneck that starves the recurrent dynamics of the information needed for accurate prediction.

**Scale of failure**: Not marginal. Not within noise. 2.2× worse is a dramatic, unambiguous failure.

---

## Failure 2: Collapse Prevention Irrelevance

**What was hoped**: OLP's proven ability to prevent posterior collapse (AFM Phase 4.6) would provide value in RSSM by ensuring stable latent states during training.

**What happened**: No model collapses. Not vanilla, not β-VAE, not OLP, not OLP+KL. The RSSM's GRU-based architecture provides a strong inductive bias against collapse. At β=0.001 on Moving-MNIST, posterior collapse simply does not occur.

**Root cause**: The GRU's recurrent structure creates a powerful prior that prevents the posterior from collapsing to the prior. The deterministic path (h_t) maintains information across timesteps independently of the stochastic path. This makes the stochastic state "useful" even without OLP.

**What this means**: OLP's one proven benefit from AFM-Lite (collapse prevention at scale) is irrelevant in the RSSM architecture. There is no pathology for OLP to cure.

---

## Failure 3: Drift Non-Improvement

**What was hoped**: OLP's orthogonal constraint would reduce representation drift by keeping the stochastic state on a well-defined manifold, providing temporal consistency.

**What happened**: OLP alone has drift of 0.998 (near-maximum), while β-VAE has drift of 0.804. The drift reduction comes from KL regularization, not from the Stiefel projection.

**Root cause**: The QR projection is a nonlinear mapping. Small changes in the raw Gaussian input can produce large changes on the Stiefel manifold. This amplifies temporal noise instead of dampening it. In contrast, KL regularization (which pushes the posterior toward the prior) creates temporal consistency by making consecutive posteriors more similar.

**What this means**: The AFM-Lite claim that "Stiefel rigidity reduces forgetting" was already weakened by Phase 4.6 (it reverses on standard benchmarks). Now we see that even the temporal stability aspect fails — OLP does NOT reduce drift in RSSM.

---

## Failure 4: Silhouette Degradation

**What was hoped**: OLP's consistent improvement of silhouette score in AFM-Lite (+25-58% across all conditions) would transfer to RSSM, producing better-separated latent representations.

**What happened**: OLP slightly worsens silhouette score (-0.033 vs -0.027 for vanilla). OLP+KL dramatically worsens it (-0.059).

**Root cause**: Two factors:
1. In RSSM, latents encode dynamics (motion + identity), not just identity. Silhouette measures identity clustering, which is not the primary latent structure.
2. The Stiefel constraint reduces the capacity to encode identity-relevant information alongside dynamic information.

**What this means**: The most robust finding from AFM-Lite (silhouette improvement in VAEs) does NOT transfer to RSSMs. The benefit was specific to static VAE architectures.

---

## Failure 5: KL Rescue Is Not an OLP Victory

**What was observed**: OLP+KL has prediction MSE of 0.037, slightly better than β-VAE's 0.040.

**Why this is not a success**:
1. The improvement is 6.6% — within noise for 3 seeds
2. OLP+KL has WORSE silhouette (-0.059 vs -0.029) and WORSE drift (0.898 vs 0.804)
3. β-VAE alone achieves similar or better results on most metrics
4. The OLP component is net-negative; only the KL component helps

**The honest assessment**: OLP+KL ≈ β-VAE with extra steps and worse side effects.

---

## Comparison to AFM-Lite Results

| Effect | AFM-Lite (VAE) | OLP Phase 5 (RSSM) | Transfer? |
|---|---|---|---|
| Collapse prevention | PARTIALLY_PROVEN (1.33M scale) | Irrelevant (no collapse in RSSM) | ❌ |
| Silhouette improvement | PROVEN (+25-58%) | FAILED (slightly worse) | ❌ |
| Accuracy improvement | PARTIALLY_PROVEN (+0.24%) | FAILED (-120% MSE) | ❌ |
| Forgetting reduction | FAILED (standard benchmarks) | FAILED (drift not improved) | ❌ |
| Training stability | Not primary focus | PARTIALLY_PROVEN (marginal) | ⚠️ |

**0 out of 4 primary AFM effects transfer to RSSM.**

---

## Why OLP Failed in RSSM

The fundamental reason is architectural:

1. **VAE**: The Stiefel projection is applied once (encoder → Stiefel → decoder). The constraint acts as a regularizer at a single bottleneck. If the bottleneck doesn't need the constraint (no collapse), the constraint is neutral to mildly harmful.

2. **RSSM**: The Stiefel projection is applied every timestep and its output is fed into a GRU. The constraint acts as a continuous bottleneck that starves the recurrent dynamics. Even if the constraint is individually mild, its effect compounds over time.

3. **Information theory**: St(8,4) has 8×4=32 dimensions but only K=4=4 effective degrees of freedom. This is a 87.5% reduction in effective capacity. In a VAE, the decoder can compensate by learning to extract information from the Stiefel structure. In an RSSM, the GRU cannot compensate because it receives the constrained state every timestep.

---

## What Would Need to Change for OLP to Work in RSSM

1. **Much larger K**: Use St(32, 16) instead of St(8, 4). This would give 16 effective directions instead of 4, reducing the information bottleneck. But this increases computational cost and may negate any benefit.

2. **Apply OLP to deterministic state only**: Instead of constraining the stochastic path, apply QR to the deterministic GRU hidden state. This would orthogonalize the recurrent dynamics without constraining the stochastic information flow. But this is a fundamentally different architecture.

3. **Use OLP only for collapse-prone regimes**: Only apply QR when collapse is detected. This would preserve information flow in normal operation while providing collapse prevention when needed. But this requires a collapse detection mechanism.

4. **Larger scale**: The AFM-Lite collapse benefit emerged at 1.33M parameters. Perhaps RSSM collapse occurs at larger scales (10M+). Testing this would require much more compute.

**None of these are recommended.** Each adds complexity without evidence of benefit. The failure policy states: if OLP hurts performance, document it. Do not rescue it with additional complexity.

---

*Report generated by OLP Phase 5*
*All failures documented honestly.*
*No rescue attempts made.*
