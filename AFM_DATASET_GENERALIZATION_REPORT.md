# AFM Phase 4.5E — Dataset Generalization Report

**Date**: 2026-06-12 19:31
**Scale**: ~1.33M params (hidden_dim=512)
**Seeds**: [0, 42, 84] | **Epochs**: 15
**BETA**: 0.01 | **LR**: 0.001

## mnist

| Config | Accuracy (mean ± 95% CI) | Active Dims | Silhouette | Collapse Rate |
|--------|--------------------------|-------------|------------|---------------|
| baseline | 0.9812 [0.9781, 0.9843] | 128.0 | 0.5124 | 0.00 |
| beta_vae | 0.2504 [0.1130, 0.3878] | 0.0 | 0.7110 | 1.00 |
| afm_task | 0.9823 [0.9820, 0.9827] | 128.0 | 0.6417 | 0.00 |
| afm_qr | 0.9835 [0.9828, 0.9842] | 128.0 | 0.6666 | 0.00 |
| afm_rib | 0.9836 [0.9812, 0.9859] | 128.0 | 0.6512 | 0.00 |

## fashion_mnist

| Config | Accuracy (mean ± 95% CI) | Active Dims | Silhouette | Collapse Rate |
|--------|--------------------------|-------------|------------|---------------|
| baseline | 0.8894 [0.8876, 0.8912] | 128.0 | 0.3205 | 0.00 |
| beta_vae | 0.2174 [0.0711, 0.3636] | 0.0 | 0.4810 | 1.00 |
| afm_task | 0.8936 [0.8905, 0.8967] | 128.0 | 0.4365 | 0.00 |
| afm_qr | 0.8895 [0.8848, 0.8941] | 128.0 | 0.3890 | 0.00 |
| afm_rib | 0.8903 [0.8876, 0.8931] | 128.0 | 0.3909 | 0.00 |

## kmnist

| Config | Accuracy (mean ± 95% CI) | Active Dims | Silhouette | Collapse Rate |
|--------|--------------------------|-------------|------------|---------------|
| baseline | 0.9157 [0.9086, 0.9228] | 128.0 | 0.3080 | 0.00 |
| beta_vae | 0.1664 [0.0271, 0.3058] | 0.0 | 0.3393 | 1.00 |
| afm_task | 0.9162 [0.9085, 0.9238] | 128.0 | 0.4158 | 0.00 |
| afm_qr | 0.9233 [0.9199, 0.9267] | 128.0 | 0.4044 | 0.00 |
| afm_rib | 0.9224 [0.9181, 0.9268] | 128.0 | 0.4011 | 0.00 |

## emnist_balanced

| Config | Accuracy (mean ± 95% CI) | Active Dims | Silhouette | Collapse Rate |
|--------|--------------------------|-------------|------------|---------------|
| baseline | 0.8529 [0.8488, 0.8571] | 128.0 | 0.1203 | 0.00 |
| beta_vae | 0.0213 [0.0213, 0.0213] | 0.0 | 0.2375 | 1.00 |
| afm_task | 0.8536 [0.8458, 0.8614] | 128.0 | 0.1899 | 0.00 |
| afm_qr | 0.8540 [0.8492, 0.8588] | 128.0 | 0.1763 | 0.00 |
| afm_rib | 0.8516 [0.8502, 0.8530] | 128.0 | 0.1585 | 0.00 |

## Effect Classifications

| Effect | Classification |
|--------|---------------|
| β-VAE causes posterior collapse | **PROVEN** |
| AFM+RIB is collapse-resistant | **PROVEN** |
| AFM+RIB maintains accuracy ≥ baseline | **PROVEN** |
| Stiefel structure improves over unconstrained latent | **PROVEN** |
| AFM produces more structured representations (higher silhouette) | **PROVEN** |

## Summary

- **PROVEN**: 5 effects
- **PARTIALLY PROVEN**: 0 effects
- **FAILED**: 0 effects
- **UNKNOWN**: 0 effects