# OLP Phase 5 — Hypothesis Report

> **Program**: OLP Phase 5 — RSSM Integration
> **Date**: 2026-06-12
> **Classification System**: PROVEN / PARTIALLY_PROVEN / FAILED / UNKNOWN
> **Rule**: Evidence over elegance. No rescue attempts.

---

## Hypotheses Tested

### P5-H1: OLP Improves Prediction Accuracy in RSSM

**Classification: FAILED**

**Prediction MSE across conditions:**

| Condition | Mean MSE | Std |
|---|---|---|
| Vanilla RSSM | 0.0404 | 0.002 |
| RSSM + β-VAE | 0.0396 | 0.001 |
| RSSM + OLP | **0.0888** | **0.011** |
| RSSM + OLP + KL | 0.0370 | 0.001 |

OLP alone produces 2.2× worse prediction than vanilla. This is not a marginal degradation — it is a dramatic failure. The QR projection constrains the stochastic path so severely that the model cannot encode sufficient information for accurate prediction.

OLP+KL partially recovers (0.037 vs vanilla 0.040), but this small advantage (6.6%) is not statistically significant with 3 seeds and comes at the cost of worse silhouette and drift.

**Why OLP hurts prediction**: In a VAE, the Stiefel projection maps the latent to a compact manifold, but the decoder receives the full flattened St(8,4) point (32 dimensions). In an RSSM, the stochastic state z is used at every timestep as input to the deterministic GRU. The QR projection forces z to live on a manifold with limited expressivity — a 32-dimensional vector constrained to have only 4 "effective" directions (K=4 orthogonal threads). This bottleneck starves the GRU of information.

**Verdict**: OLP does NOT improve prediction in RSSM. It dramatically worsens it.

---

### P5-H2: OLP Prevents Latent Collapse in RSSM

**Classification: FAILED (not because it doesn't work, but because there's nothing to prevent)**

| Condition | Collapse Rate | Active Dimensions |
|---|---|---|
| Vanilla RSSM | 0.0% | 100% |
| RSSM + β-VAE | 0.0% | 100% |
| RSSM + OLP | 0.0% | 100% |
| RSSM + OLP + KL | 0.0% | 100% |

No model collapses at this scale and β setting. The RSSM architecture with temporal recurrence (GRU) and β=0.001 does not exhibit posterior collapse. The GRU provides a strong inductive bias that keeps representations active.

The collapse prevention benefit of OLP that was observed in AFM-Lite (at 1.33M parameters) does not transfer because RSSM at this scale doesn't collapse in the first place.

**Verdict**: OLP's collapse prevention is irrelevant in this RSSM configuration.

---

### P5-H3: OLP Reduces Representation Drift in RSSM

**Classification: FAILED**

| Condition | Drift Mean | Drift Std |
|---|---|---|
| Vanilla RSSM | 0.996 | 0.005 |
| RSSM + β-VAE | **0.804** | 0.003 |
| RSSM + OLP | 0.998 | 0.005 |
| RSSM + OLP + KL | 0.898 | 0.014 |

OLP alone has drift ≈ 1.0 (near-maximum), meaning consecutive timesteps produce nearly orthogonal representations. β-VAE has the lowest drift (0.804). The drift reduction comes from KL regularization, not from the Stiefel projection.

In fact, OLP appears to INCREASE drift slightly compared to vanilla (0.998 vs 0.996), though the difference is within noise.

**Why OLP doesn't reduce drift**: The QR projection is not an identity mapping — it rotates the representation. When the raw Gaussian input changes between timesteps, the QR decomposition produces a very different Stiefel point. The projection amplifies small changes in the input into large changes on the manifold.

**Verdict**: OLP does NOT reduce representation drift. KL regularization does.

---

### P5-H4: OLP Improves Silhouette Score in RSSM

**Classification: FAILED**

| Condition | Silhouette Score |
|---|---|
| Vanilla RSSM | -0.027 |
| RSSM + β-VAE | -0.029 |
| RSSM + OLP | -0.033 |
| RSSM + OLP + KL | **-0.059** |

All silhouette scores are negative, indicating poor cluster separation. This is fundamentally different from the AFM-Lite finding where OLP improved silhouette from 0.37 to 0.68.

**Why the contradiction**: In AFM-Lite (VAE), the latent represents a single observation. Digit identity correlates strongly with latent structure, and OLP's orthogonal constraint distributes this structure well. In RSSM, the latent represents a temporal state that encodes both identity AND motion. The "cluster structure" that silhouette measures (digit identity) is not the primary information in RSSM latents (which encode dynamics). OLP constraining these dynamic representations actually worsens their quality.

**Verdict**: OLP does NOT improve silhouette in RSSM. It worsens it.

---

### P5-H5: OLP Improves Training Stability in RSSM

**Classification: PARTIALLY_PROVEN (marginally)**

| Condition | Stability CV |
|---|---|
| Vanilla RSSM | 0.075 |
| RSSM + β-VAE | 0.052 |
| RSSM + OLP | 0.067 |
| RSSM + OLP + KL | 0.053 |

OLP slightly improves stability CV compared to vanilla (0.067 vs 0.075), but the improvement is small and is also achieved by β-VAE alone (0.052). The stability benefit appears to come from regularization in general, not from OLP specifically.

**Verdict**: OLP provides marginal stability improvement that is also achievable through KL regularization alone.

---

## Summary Table

| Hypothesis | Classification | Confidence | Key Evidence |
|---|---|---|---|
| P5-H1: OLP improves prediction | **FAILED** | Very High | OLP MSE is 2.2× worse than vanilla |
| P5-H2: OLP prevents collapse | **FAILED** | Very High | No model collapses. Effect is irrelevant here. |
| P5-H3: OLP reduces drift | **FAILED** | Very High | OLP drift ≈ 1.0. KL reduces drift, not OLP. |
| P5-H4: OLP improves silhouette | **FAILED** | Very High | OLP worsens silhouette. AFM result does not transfer. |
| P5-H5: OLP improves stability | **PARTIALLY_PROVEN** | Low | Marginal improvement. KL achieves same effect. |

---

*Report generated by OLP Phase 5*
*Four of five hypotheses FAILED. One marginally supported.*
*Evidence alone decides.*
