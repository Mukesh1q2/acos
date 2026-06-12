# AFM Phase 4.5A — Multi-Seed Validation Report

**Date**: 2026-06-12 18:15
**Scale**: ~1.33M params (hidden_dim=512)
**Dataset**: Fashion-MNIST | **Seeds**: [0, 42, 84, 126, 168] | **Epochs**: 15
**BETA**: 0.01 | **LR**: 0.001 | **Batch**: 256

## Summary Statistics (mean ± 95% CI)

| Config | Test Accuracy | Active Dims | Silhouette | Recon Loss | Collapse Rate |
|--------|--------------|-------------|------------|------------|---------------|
| baseline | 0.8908 [0.8883, 0.8933] | 128.0 [128.0, 128.0] | 0.3196 | 297.7061 | 0.00 |
| beta_vae | 0.2205 [0.1628, 0.2782] | 0.0 [0.0, 0.0] | 0.4747 | 163.3950 | 1.00 |
| afm_task | 0.8929 [0.8913, 0.8946] | 128.0 [128.0, 128.0] | 0.4335 | 164.9093 | 0.00 |
| afm_qr | 0.8905 [0.8876, 0.8934] | 128.0 [128.0, 128.0] | 0.3799 | 164.9424 | 0.00 |
| afm_rib | 0.8898 [0.8882, 0.8913] | 128.0 [128.0, 128.0] | 0.3854 | 164.8098 | 0.00 |


## baseline

- **test_accuracy**: 0.8908 ± 0.0020 (95% CI: [0.8883, 0.8933], n=5)
- **active_dims**: 128.0000 ± 0.0000 (95% CI: [128.0000, 128.0000], n=5)
- **silhouette_score**: 0.3196 ± 0.0099 (95% CI: [0.3073, 0.3320], n=5)
- **reconstruction_loss**: 297.7061 ± 17.8864 (95% CI: [275.4971, 319.9150], n=5)
- **Collapse rate**: 0.00 (0/5 runs)

## beta_vae

- **test_accuracy**: 0.2205 ± 0.0465 (95% CI: [0.1628, 0.2782], n=5)
- **active_dims**: 0.0000 ± 0.0000 (95% CI: [0.0000, 0.0000], n=5)
- **silhouette_score**: 0.4747 ± 0.0162 (95% CI: [0.4546, 0.4948], n=5)
- **reconstruction_loss**: 163.3950 ± 0.3983 (95% CI: [162.9004, 163.8896], n=5)
- **Collapse rate**: 1.00 (5/5 runs)

## afm_task

- **test_accuracy**: 0.8929 ± 0.0013 (95% CI: [0.8913, 0.8946], n=5)
- **active_dims**: 128.0000 ± 0.0000 (95% CI: [128.0000, 128.0000], n=5)
- **silhouette_score**: 0.4335 ± 0.0092 (95% CI: [0.4220, 0.4450], n=5)
- **reconstruction_loss**: 164.9093 ± 0.6624 (95% CI: [164.0869, 165.7318], n=5)
- **Collapse rate**: 0.00 (0/5 runs)

## afm_qr

- **test_accuracy**: 0.8905 ± 0.0023 (95% CI: [0.8876, 0.8934], n=5)
- **active_dims**: 128.0000 ± 0.0000 (95% CI: [128.0000, 128.0000], n=5)
- **silhouette_score**: 0.3799 ± 0.0262 (95% CI: [0.3473, 0.4125], n=5)
- **reconstruction_loss**: 164.9424 ± 0.2054 (95% CI: [164.6873, 165.1975], n=5)
- **Collapse rate**: 0.00 (0/5 runs)

## afm_rib

- **test_accuracy**: 0.8898 ± 0.0013 (95% CI: [0.8882, 0.8913], n=5)
- **active_dims**: 128.0000 ± 0.0000 (95% CI: [128.0000, 128.0000], n=5)
- **silhouette_score**: 0.3854 ± 0.0178 (95% CI: [0.3633, 0.4076], n=5)
- **reconstruction_loss**: 164.8098 ± 0.4882 (95% CI: [164.2036, 165.4160], n=5)
- **Collapse rate**: 0.00 (0/5 runs)

## Key Findings

- **β-VAE collapse confirmed**: Standard KL regularization causes posterior collapse (5/5 runs collapsed)
- **AFM+RIB does NOT outperform baseline**: 0.8898 vs 0.8908
- **AFM+RIB is collapse-resistant**: 0/5 runs collapsed (vs β-VAE collapse)