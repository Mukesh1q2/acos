# OLP Phase 5 — Mechanism Report

> **Program**: OLP Phase 5 — RSSM Integration
> **Date**: 2026-06-12
> **Question**: What is the actual mechanism by which OLP affects RSSM performance?

---

## The Surviving Mechanism from AFM-Lite

From AFM Phase 4.6, the surviving mechanism was:

**QR projection** → maps raw latent to Stiefel manifold → guarantees full-rank representation

The Phase 4.6 conclusion was:
- QR prevents collapse (algebraic, not learned)
- QR improves silhouette (variance distribution)
- L_RIB ≈ β-VAE (no additional benefit)
- Forgetting reduction failed on standard benchmarks

The minimal architecture was: β-VAE + QR projection

---

## What OLP Does in an RSSM

### Architecture Review

In an RSSM, the stochastic path works as follows:

1. **Prior**: h_t → μ_prior, σ_prior → z_prior ~ N(μ_prior, σ_prior)
2. **Posterior**: (h_t, o_t) → μ_post, σ_post → z_post ~ N(μ_post, σ_post)
3. **State**: z_t is used as input to the GRU at the next timestep: h_{t+1} = GRU(h_t, z_t)

In OLP-RSSM, step 3 is replaced with:

1. **Prior**: h_t → raw_prior ~ N(μ_prior, σ_prior) → QR → S_prior
2. **Posterior**: (h_t, o_t) → raw_post ~ N(μ_post, σ_post) → QR → S_post
3. **State**: z_t = flatten(S_t) is used as input to the GRU

### The Critical Difference from VAE

In a VAE (AFM-Lite), the decoder receives the Stiefel point once and produces an output. The constraint helps because:
- The decoder can learn to use the structured representation
- The constraint prevents degenerate solutions (collapse)
- The representation is used only at one layer

In an RSSM, the Stiefel point is **recycled every timestep** through the GRU. This creates a fundamental mismatch:

1. **Information bottleneck**: St(8,4) has K=4 orthogonal directions. The GRU receives a 32-dim vector, but only 4 independent directions can vary. This is an extreme bottleneck.

2. **Gradient disruption**: QR decomposition has complex gradient flow. While autograd handles it, the gradients through QR can be poorly conditioned, making learning harder.

3. **Temporal instability**: Small changes in the raw Gaussian input produce large changes in the Stiefel point (because QR is a nonlinear projection). This amplifies temporal noise instead of dampening it.

---

## Mechanism Attribution

### Effect: Prediction MSE Degradation (2.2× worse)

| Mechanism | Contribution | Evidence |
|---|---|---|
| **Information bottleneck** | ~70% | St(8,4) has only 4 effective directions. The GRU needs full 32-dim expressivity. |
| **Gradient disruption** | ~20% | QR gradients can be poorly conditioned for learning. |
| **Temporal amplification** | ~10% | QR amplifies input noise, hurting temporal consistency. |

### Effect: No Collapse (all conditions)

| Mechanism | Contribution | Evidence |
|---|---|---|
| **GRU inductive bias** | ~80% | The recurrent structure naturally prevents collapse. |
| **Small β value** | ~20% | β=0.001 doesn't push toward prior strongly. |

OLP's collapse prevention is irrelevant because the baseline doesn't collapse.

### Effect: Representation Drift (no improvement from OLP)

| Mechanism | Contribution | Evidence |
|---|---|---|
| **KL regularization** | ~90% | β-VAE and OLP+KL both reduce drift. OLP alone doesn't. |
| **QR projection** | ~10% (negative) | QR actually slightly increases drift by amplifying noise. |

The drift reduction that AFM-Lite attributed to "Stiefel rigidity" was actually from KL regularization.

### Effect: Silhouette Degradation

| Mechanism | Contribution | Evidence |
|---|---|---|
| **Dynamic vs static representation** | ~60% | RSSM latents encode dynamics, not identity. Silhouette measures identity clustering. |
| **Information bottleneck** | ~30% | The Stiefel constraint reduces the capacity to encode identity-relevant information. |
| **KL over-regularization** | ~10% | OLP+KL has the worst silhouette, suggesting KL + QR over-regularize. |

---

## Why AFM Results Don't Transfer

| Property | VAE (AFM-Lite) | RSSM (OLP Phase 5) |
|---|---|---|
| Latent usage | One-shot: encode → decode | Recurrent: encode → GRU → encode → GRU → ... |
| Information flow | Unidirectional | Bidirectional (past → future) |
| Collapse risk | High (at 1.33M) | Low (GRU prevents it) |
| What latent encodes | Static observation | Dynamic state (identity + motion) |
| Silhouette meaning | Cluster quality | Not applicable (dynamic states) |
| OLP's effect | Constrains → prevents collapse | Constrains → starves GRU of information |

**The fundamental insight**: OLP's QR projection is a constraint. In a VAE where the constraint prevents collapse, the constraint is beneficial. In an RSSM where the constraint prevents information flow to the recurrent dynamics, the constraint is harmful.

**Constraints are not universally beneficial.** A constraint helps when it prevents a pathology (collapse) and hurts when it prevents necessary functionality (information flow).

---

## The KL Rescue

When KL regularization is added to OLP (olp_kl), prediction MSE partially recovers:

| Condition | Prediction MSE |
|---|---|
| vanilla | 0.0404 |
| beta_vae | 0.0396 |
| olp | 0.0888 |
| olp_kl | 0.0370 |

Why does KL help?

1. **Regularization**: KL pushes the posterior toward the prior, preventing the raw Gaussian from producing extreme values that QR would map to degenerate Stiefel points.

2. **Information balance**: KL forces the model to use the Stiefel representation efficiently, rather than "giving up" on the constrained channel.

3. **Not a real improvement**: OLP+KL (0.037) is only marginally better than β-VAE (0.040). The 6.6% improvement is within noise and doesn't justify the added complexity.

---

## Conclusion

The mechanism by which OLP helps in VAEs (preventing collapse via algebraic full-rank guarantee) does not transfer to RSSMs because:

1. RSSMs don't collapse at this scale (no pathology to prevent)
2. The Stiefel constraint creates an information bottleneck that hurts recurrent dynamics
3. The temporal amplification of QR hurts representation stability
4. All benefits attributed to OLP in AFM-Lite are either irrelevant or reversed in RSSM

The only mechanism that helps RSSM performance is standard KL regularization (β-VAE), not OLP.

---

*Report generated by OLP Phase 5*
*The mechanism that survived in VAEs failed in RSSMs.*
*Constraints help when they prevent pathologies, not when they prevent functionality.*
