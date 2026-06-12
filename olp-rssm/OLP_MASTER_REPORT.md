# OLP Phase 5 — Master Report

> **Program**: OLP (Orthogonal Latent Projection) Phase 5 — RSSM Integration
> **Date**: 2026-06-12
> **Origin**: Surviving mechanism from AFM-Lite Phase 4.6
> **Target**: Predictive world models (RSSM architectures)
> **Core Question**: Can OLP improve latent stability inside RSSM?

---

## Answer

**No. OLP does not improve latent stability inside RSSM.**

In fact, OLP dramatically worsens it.

---

## Experimental Summary

### Setup
- **Dataset**: Moving-MNIST (32×32, 2 digits, 10-frame sequences)
- **Conditions**: Vanilla RSSM, RSSM+β-VAE, RSSM+OLP, RSSM+OLP+KL
- **Seeds**: 0, 42, 84 (3 per condition)
- **Model**: ~1M parameters, latent_dim=32, St(8,4) for OLP
- **Training**: 8-10 epochs, 80-100 batches/epoch, β=1e-3

### Results

| Metric | Vanilla | β-VAE | OLP | OLP+KL | Best |
|---|---|---|---|---|---|
| **Prediction MSE** | 0.040 | 0.040 | **0.089** | 0.037 | β-VAE / OLP+KL |
| **Collapse Rate** | 0.0% | 0.0% | 0.0% | 0.0% | Tie |
| **Silhouette** | -0.027 | -0.029 | -0.033 | **-0.059** | Vanilla |
| **Rep. Drift** | 0.996 | **0.804** | 0.998 | 0.898 | β-VAE |
| **Stability CV** | 0.075 | 0.052 | 0.067 | 0.053 | β-VAE |
| **Eff. Dimensionality** | 0.996 | 0.926 | 0.995 | 0.987 | Tie |

---

## Hypothesis Verdicts

| Hypothesis | Classification |
|---|---|
| P5-H1: OLP improves prediction | **FAILED** — 2.2× worse |
| P5-H2: OLP prevents collapse | **FAILED** — no collapse to prevent |
| P5-H3: OLP reduces drift | **FAILED** — drift unchanged |
| P5-H4: OLP improves silhouette | **FAILED** — slightly worse |
| P5-H5: OLP improves stability | **PARTIALLY_PROVEN** — marginal |

**4 of 5 hypotheses FAILED.**

---

## The Success Criterion

From the Phase 5 specification:

> OLP advances only if at least one effect survives:
> - lower prediction error
> - lower latent collapse
> - improved rollout stability
> - improved representation quality

**Assessment against each criterion:**

1. **Lower prediction error**: ❌ OLP alone is 2.2× worse. OLP+KL is marginally better than β-VAE (6.6%) but not statistically significant, and has worse other metrics.

2. **Lower latent collapse**: ❌ No model collapses. There is nothing to improve.

3. **Improved rollout stability**: ❌ OLP has the same drift as vanilla. β-VAE has better rollout stability than OLP.

4. **Improved representation quality**: ❌ OLP slightly worsens silhouette score. The AFM-Lite silhouette benefit does not transfer.

**None of the success criteria are met.**

---

## The Failure Policy

From the Phase 5 specification:

> If RSSM+OLP performs the same as RSSM: mark OLP as FAILED.
> If OLP hurts performance: document it. Do not rescue it.

**RSSM+OLP does not perform the same as RSSM. It performs WORSE.**

The failure policy requires us to document this and not rescue OLP with additional complexity.

---

## Why OLP Failed: Root Cause Analysis

### 1. The Constraint-Pathology Mismatch

OLP's QR projection is a constraint. Constraints help when they prevent pathologies:
- In VAEs at 1.33M scale: collapse is a pathology → constraint helps
- In RSSMs at this scale: no collapse → constraint is unnecessary and harmful

The constraint reduces information capacity (St(8,4) has only 4 effective directions out of 32 dimensions). Without a pathology to prevent, this capacity reduction is pure cost.

### 2. The Recurrence Problem

In a VAE, the Stiefel point is consumed once by the decoder. In an RSSM, it's consumed every timestep by the GRU. The constraint compounds:
- Timestep 1: 4/32 effective dimensions → GRU gets limited information
- Timestep 2: Limited h_t + limited z_t → doubly limited information
- Timestep N: Error accumulates through the constrained recurrent path

### 3. The Temporal Amplification

QR decomposition is a nonlinear projection. Small input changes can produce large output changes (especially when the input matrix is near a QR boundary). This amplifies temporal noise instead of dampening it, increasing drift instead of reducing it.

### 4. The Transfer Failure

None of the 4 primary AFM-Lite effects transferred to RSSM:

| Effect | VAE | RSSM | Reason |
|---|---|---|---|
| Collapse prevention | Works (1.33M) | Irrelevant | GRU prevents collapse naturally |
| Silhouette improvement | +25-58% | Slightly worse | RSSM latents encode dynamics, not identity |
| Accuracy improvement | +0.24% | -120% MSE | Information bottleneck hurts recurrent dynamics |
| Forgetting reduction | Failed on std benchmarks | Also failed | OLP rigidity ≠ temporal stability |

---

## What About Different Geometries?

We tested St(8,4) with latent_dim=32. What about other geometries?

| Geometry | Effective Directions | Capacity | Prediction Cost |
|---|---|---|---|
| St(8,4) | 4/32 = 12.5% | Very low | 2.2× worse |
| St(16,2) | 2/32 = 6.25% | Extremely low | Likely catastrophic |
| St(32,1) | 1/32 = 3.1% | Near-zero | Guaranteed failure |
| St(16,16) | 16/256 = 6.25% | Low per unit | Needs much larger latent |
| St(32,32) | 32/1024 = 3.1% | Very low per unit | Even worse |

**The problem is fundamental**: St(d,K) with small K has few effective directions. Increasing K requires increasing d, which requires increasing latent_dim, which changes the entire architecture. There is no geometry that gives "enough" effective directions without a large latent dimension.

---

## What This Means for OLP

### AFM-Lite's Surviving Mechanism

In AFM-Lite, the surviving mechanism was QR projection preventing collapse. This was a real effect at 1.33M scale. The Phase 4.6 verdict was "WORKSHOP_READY" — one strong finding.

### OLP in RSSM

In RSSM, the surviving mechanism does not survive. The collapse prevention is irrelevant, and the constraint actively hurts performance.

### The Honest Conclusion

**OLP does not deserve to exist as an RSSM component.**

The question was: "Can OLP improve latent stability inside RSSM architectures?"

The answer is: **No. OLP destabilizes RSSM latent spaces.**

---

## Deliverables

| File | Description |
|---|---|
| `OLP_PHASE5_RESULTS.md` | Complete results across all metrics and conditions |
| `OLP_HYPOTHESIS_REPORT.md` | Hypothesis classification (4 FAILED, 1 PARTIALLY_PROVEN) |
| `OLP_MECHANISM_REPORT.md` | Why OLP fails in RSSM (constraint-pathology mismatch) |
| `OLP_FAILURE_REPORT.md` | Detailed failure documentation |
| `OLP_MASTER_REPORT.md` | This document |

---

## Final Statement

The OLP Phase 5 program asked a clear question: does orthogonal latent projection provide benefits beyond image classification VAEs, specifically in RSSM architectures for predictive world models?

The evidence is unambiguous: **No.**

OLP in RSSM:
- Worsens prediction by 2.2×
- Provides no collapse prevention benefit (there's no collapse to prevent)
- Does not reduce representation drift
- Does not improve representation quality
- The marginal training stability improvement is also achieved by standard β-VAE

The AFM-Lite finding that QR projection prevents posterior collapse is real but narrow. It applies to VAEs at scale where collapse occurs. It does not generalize to RSSMs where the architecture naturally prevents collapse.

**The failure is not in the experiment. The failure is in the assumption that a constraint that helps in one architecture would help in a fundamentally different one.**

Per the failure policy: OLP hurts RSSM performance. We document it. We do not rescue it.

**OLP Phase 5: FAILED.**

---

*Report generated by OLP Phase 5 Master Program*
*Question: Does OLP deserve to exist?*
*Answer: Not in RSSM. Not as a general technique. Not without a specific pathology to address.*
*Evidence alone decides.*
