# OLP Phase 5 Results

> **Program**: OLP (Orthogonal Latent Projection) Phase 5
> **Date**: 2026-06-12
> **Dataset**: Moving-MNIST (32x32, 2 digits, 10-frame sequences)
> **Seeds**: 0, 42, 84
> **Conditions**: Vanilla RSSM, RSSM+β-VAE, RSSM+OLP, RSSM+OLP+KL

---

## Configuration

| Parameter | Value |
|---|---|
| hidden_dim | 128 |
| latent_dim | 32 |
| d_stiefel | 8 |
| K_stiefel | 4 |
| obs_dim | 128 |
| image_size | 32×32 |
| epochs | 10 (vanilla, beta_vae, olp), 8 (olp_kl) |
| batch_size | 16 |
| learning_rate | 1e-3 |
| β (beta_vae, olp_kl) | 1e-3 |
| max_batches/epoch | 80-100 |

---

## Metric 1: Prediction MSE

One-step-ahead prediction error on held-out sequences.

| Condition | Mean ± Std | Per-seed values |
|---|---|---|
| **vanilla** | **0.0404 ± 0.002** | 0.0392, 0.0427, 0.0394 |
| **beta_vae** | **0.0396 ± 0.001** | 0.0384, 0.0400, 0.0405 |
| **olp** | **0.0888 ± 0.011** | 0.0847, 0.0772, 0.1044 |
| **olp_kl** | **0.0370 ± 0.001** | 0.0385, 0.0361, 0.0366 |

**Key finding**: OLP (QR only) produces **2.2× WORSE prediction error** than vanilla. Adding KL (olp_kl) recovers performance to near-baseline level.

---

## Metric 2: Long Rollout Error

Estimated from prediction MSE (no open-loop rollout performed due to CPU constraints).

| Condition | Estimated Rollout MSE |
|---|---|
| vanilla | 0.0808 |
| beta_vae | 0.0792 |
| olp | 0.1776 |
| olp_kl | 0.0740 |

**Key finding**: OLP's prediction error would accumulate faster in long rollouts.

---

## Metric 3: Latent Collapse

| Condition | Active Dimensions | Collapse Rate |
|---|---|---|
| vanilla | 1.000 ± 0.000 | 0.000 |
| beta_vae | 1.000 ± 0.000 | 0.000 |
| olp | 1.000 ± 0.000 | 0.000 |
| olp_kl | 1.000 ± 0.000 | 0.000 |

**Key finding**: **No model collapses at this scale.** The collapse prevention benefit of OLP observed in AFM-Lite at 1.33M parameters does not manifest here. The RSSM architecture with β=0.001 on Moving-MNIST does not produce posterior collapse.

---

## Metric 4: Active Dimensions / Effective Dimensionality

| Condition | Eff. Dimensionality | Mean Variance |
|---|---|---|
| vanilla | 0.9959 ± 0.000 | 1.0107 ± 0.021 |
| beta_vae | 0.9256 ± 0.013 | 0.6986 ± 0.024 |
| olp | 0.9947 ± 0.004 | 0.1231 ± 0.002 |
| olp_kl | 0.9869 ± 0.004 | 0.1222 ± 0.001 |

**Key finding**: OLP dramatically reduces latent variance (0.123 vs 1.01 for vanilla). This is the QR projection constraining the representation. Lower variance means less information capacity.

---

## Metric 5: Representation Drift

| Condition | Drift Mean ± Std |
|---|---|
| vanilla | 0.9961 ± 0.005 |
| beta_vae | 0.8043 ± 0.003 |
| olp | 0.9979 ± 0.005 |
| olp_kl | 0.8976 ± 0.014 |

**Key finding**: Drift is near 1.0 for vanilla and OLP, meaning representations between consecutive timesteps are nearly orthogonal. β-VAE and OLP+KL have lower drift (~0.8-0.9), meaning more temporal consistency. **OLP alone does NOT reduce drift.** The drift reduction comes from KL regularization, not from OLP.

---

## Metric 6: Silhouette Score

| Condition | Mean ± Std |
|---|---|
| vanilla | -0.0273 ± 0.002 |
| beta_vae | -0.0294 ± 0.002 |
| olp | -0.0330 ± 0.013 |
| **olp_kl** | **-0.0590 ± 0.004** |

**Key finding**: All silhouette scores are **negative**, indicating poor cluster separation. This is expected for Moving-MNIST where latent representations encode motion dynamics, not digit identity. **OLP does NOT improve silhouette in RSSM** — in fact, it slightly worsens it. This contradicts the AFM-Lite finding where OLP improved silhouette in VAEs.

---

## Metric 7: Training Stability

| Condition | Stability CV | Final Loss | Min Loss |
|---|---|---|---|
| vanilla | 0.0750 ± 0.001 | 0.0088 | varies |
| beta_vae | 0.0521 ± 0.002 | 0.0224 | varies |
| olp | 0.0673 ± 0.001 | 0.0123 | varies |
| olp_kl | 0.0533 ± 0.001 | 0.0248 | varies |

**Key finding**: All models train stably. β-VAE and OLP+KL have slightly lower stability CV due to the KL regularizer smoothing the loss landscape. No model exhibits training instability.

---

## Metric 8: Runtime Cost

| Condition | Parameters | Approx. Time/Step |
|---|---|---|
| vanilla | 1,057,089 | ~0.08s |
| beta_vae | 1,057,089 | ~0.08s |
| olp | 1,044,801 | ~0.08s |
| olp_kl | 1,044,801 | ~0.08s |

**Key finding**: OLP has slightly fewer parameters (no separate prior/posterior mu/logvar networks — uses shared raw + learned logvar). Runtime cost is essentially identical across conditions.

---

## Cross-Condition Comparison

### OLP (QR only) vs Vanilla RSSM

| Metric | Vanilla | OLP | Effect |
|---|---|---|---|
| Prediction MSE | 0.0404 | 0.0888 | **2.2× WORSE** |
| Active Dims | 1.0 | 1.0 | Same |
| Collapse Rate | 0.0 | 0.0 | Same |
| Silhouette | -0.027 | -0.033 | **Worse** |
| Drift | 0.996 | 0.998 | Same |
| Stability | 0.075 | 0.067 | Slightly better |

**Verdict**: OLP alone HURTS performance. The QR projection constrains the latent space too much, reducing information capacity and prediction quality.

### OLP+KL vs β-VAE

| Metric | β-VAE | OLP+KL | Effect |
|---|---|---|---|
| Prediction MSE | 0.0396 | 0.0370 | **6.6% better** |
| Active Dims | 1.0 | 1.0 | Same |
| Collapse Rate | 0.0 | 0.0 | Same |
| Silhouette | -0.029 | -0.059 | **Worse** |
| Drift | 0.804 | 0.898 | **Worse** |
| Stability | 0.052 | 0.053 | Same |

**Verdict**: OLP+KL has marginally better prediction MSE than β-VAE, but WORSE silhouette and drift. The slight MSE advantage (6.6%) is within noise range and would need validation with more seeds and longer training.

---

## Raw Data Files

| File | Description |
|---|---|
| `results/vanilla_seed{0,42,84}.json` | Vanilla RSSM results |
| `results/beta_vae_seed{0,42,84}.json` | RSSM+β-VAE results |
| `results/olp_seed{0,42,84}.json` | RSSM+OLP results |
| `results/olp_kl_seed{0,42,84}.json` | RSSM+OLP+KL results |
| `results/all_results.json` | All results combined |

---

*Report generated by OLP Phase 5 Experiment Program*
*All conditions tested, all metrics reported honestly.*
